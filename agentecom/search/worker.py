"""
Decoupled Asynchronous Indexing Worker.
Ensures embedding generation and index rebuilds NEVER block agent-facing request paths.
Writes to merchant DB publish an event that this worker consumes asynchronously.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import Product, ProductEmbedding
from agentecom.search.hybrid import hybrid_engine
from agentecom.core.cache import cache

logger = logging.getLogger("agentecom.worker")

class AsyncIndexWorker:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self):
        """Start background consumer loop."""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._consume_loop())
            logger.info("Async Indexing Worker started.")

    async def stop(self):
        """Stop background worker gracefully."""
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def enqueue_job(self, job_type: str, payload: Dict[str, Any]):
        """Enqueue an asynchronous indexing job."""
        await self.queue.put({"type": job_type, "payload": payload})
        logger.info(f"Enqueued indexing job: {job_type}")

    async def _consume_loop(self):
        while self._is_running:
            try:
                job = await self.queue.get()
                job_type = job["type"]
                payload = job["payload"]
                
                if job_type == "INDEX_PRODUCT":
                    await self._process_index_product(payload["product_id"])
                elif job_type == "REINDEX_ALL":
                    await self._process_reindex_all()
                elif job_type == "DELETE_PRODUCT":
                    await self._process_delete_product(payload["sku"])

                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing index job: {e}", exc_info=True)

    async def _process_index_product(self, product_id: int):
        """Compute embedding asynchronously and update vector & BM25 indices."""
        async with AsyncSessionLocal() as session:
            stmt = select(Product).where(Product.id == product_id)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()
            if not product:
                return

            text_to_embed = f"{product.name}. Category: {product.category}. Description: {product.description}. Attributes: {product.attributes_json}"
            
            # Compute vector off-request-thread
            loop = asyncio.get_running_loop()
            dense_vector = await loop.run_in_executor(
                None,
                hybrid_engine.dense_retriever.encode_text,
                text_to_embed
            )
            
            vector_list = dense_vector.tolist()

            # Store in DB
            emb_stmt = select(ProductEmbedding).where(ProductEmbedding.product_id == product_id)
            emb_res = await session.execute(emb_stmt)
            emb_obj = emb_res.scalar_one_or_none()

            if emb_obj:
                emb_obj.embedding_json = json.dumps(vector_list)
            else:
                emb_obj = ProductEmbedding(
                    product_id=product_id,
                    embedding_json=json.dumps(vector_list)
                )
                session.add(emb_obj)

            await session.commit()
            
            # Invalidate search cache and reload memory index
            await cache.invalidate_sku(product.sku)
            await self._reload_hybrid_index_from_db(session)

    async def _process_reindex_all(self):
        """Full re-index of the entire catalog into BM25 and Dense vector indexes."""
        async with AsyncSessionLocal() as session:
            await self._reload_hybrid_index_from_db(session)
            await cache.clear()
            logger.info("Full catalog re-indexing complete.")

    async def _process_delete_product(self, sku: str):
        async with AsyncSessionLocal() as session:
            await cache.invalidate_sku(sku)
            await self._reload_hybrid_index_from_db(session)

    async def _reload_hybrid_index_from_db(self, session):
        stmt = select(Product).where(Product.is_active == True)
        result = await session.execute(stmt)
        products = result.scalars().all()

        prod_dicts = []
        precomputed_embeddings = []
        missing_embed_prods = []
        missing_texts = []

        for p in products:
            p_dict = {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "description": p.description,
                "category": p.category,
                "price": p.price,
                "attributes_json": p.attributes_json
            }
            prod_dicts.append(p_dict)

            # Check if embedding already stored
            emb_stmt = select(ProductEmbedding).where(ProductEmbedding.product_id == p.id)
            emb_res = await session.execute(emb_stmt)
            emb_obj = emb_res.scalar_one_or_none()

            if emb_obj and emb_obj.embedding_json:
                precomputed_embeddings.append(json.loads(emb_obj.embedding_json))
            else:
                precomputed_embeddings.append(None)
                missing_embed_prods.append(p)
                missing_texts.append(f"{p.name}. Category: {p.category}. Description: {p.description}. Attributes: {p.attributes_json}")

        # Batch encode any missing embeddings
        if missing_texts:
            loop = asyncio.get_running_loop()
            batch_vecs = await loop.run_in_executor(
                None,
                hybrid_engine.dense_retriever.encode_batch,
                missing_texts
            )
            vec_idx = 0
            for i, emb in enumerate(precomputed_embeddings):
                if emb is None:
                    vec_list = batch_vecs[vec_idx].tolist()
                    precomputed_embeddings[i] = vec_list
                    
                    prod_to_save = missing_embed_prods[vec_idx]
                    session.add(ProductEmbedding(
                        product_id=prod_to_save.id,
                        embedding_json=json.dumps(vec_list)
                    ))
                    vec_idx += 1
            await session.commit()

        # Build in-memory fast retrieval structures
        hybrid_engine.build_index(prod_dicts, precomputed_embeddings)

index_worker = AsyncIndexWorker()
