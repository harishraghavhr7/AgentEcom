"""
Model Fallback Middleware for LangChain and LangGraph in AgentEcom.
Implements the modelFallbackMiddleware specification:
Provides automatic model fallback on errors by retrying failed model calls
with alternative models in sequence (groq -> gemini -> openrouter).
When a model call fails, it tries the next model in the fallback list until
either a call succeeds or all models have been exhausted.
"""

import logging
from typing import List, Dict, Any, Optional, Sequence, Union, Tuple
from langchain_core.messages import BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableWithFallbacks

from agentecom.config import settings
from agentecom.agent.providers import (
    create_chat_model,
    get_candidate_cascade_order
)

logger = logging.getLogger("agentecom.middleware.fallback")


class ModelFallbackMiddleware:
    """
    Middleware that provides automatic model fallback on errors.
    This middleware attempts to retry failed model calls with alternative models in sequence.
    When a model call fails, it tries the next model in the fallback list until either
    a call succeeds or all models have been exhausted.
    """

    def __init__(
        self,
        fallback_models: Optional[Union[str, Sequence[Union[str, BaseChatModel]]]] = None,
        primary_model: Optional[Union[str, BaseChatModel]] = "groq",
        groq_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.primary_spec = primary_model or "groq"

        # Parse fallback_models into a list
        if fallback_models is None:
            raw_cascade = getattr(settings, "FALLBACK_CASCADE_ORDER", "groq,gemini,openrouter")
            models_in_cascade = [m.strip().lower() for m in raw_cascade.split(",") if m.strip()]
            primary_name = self.primary_spec if isinstance(self.primary_spec, str) else getattr(self.primary_spec, "_llm_type", "")
            self.fallback_specs: List[Union[str, BaseChatModel]] = [
                m for m in models_in_cascade if m != primary_name.lower()
            ]
        elif isinstance(fallback_models, str):
            self.fallback_specs = [m.strip() for m in fallback_models.split(",") if m.strip()]
        else:
            self.fallback_specs = list(fallback_models)

        self.groq_api_key = groq_api_key
        self.gemini_api_key = gemini_api_key
        self.openrouter_api_key = openrouter_api_key
        self.ollama_base_url = ollama_base_url
        self.model_name = model_name

    def _resolve_model(self, spec: Union[str, BaseChatModel]) -> Tuple[Optional[BaseChatModel], str]:
        """Resolves a model spec (string provider name or BaseChatModel instance) into an executable model."""
        if isinstance(spec, BaseChatModel):
            name = getattr(spec, "model_name", None) or getattr(spec, "model", None) or spec._llm_type
            return spec, str(name)

        prov = str(spec).strip().lower()
        if prov in ["local", "offline", "zero-key"]:
            return None, "local"

        model = create_chat_model(
            provider=prov,
            model_name=self.model_name if prov == str(self.primary_spec).lower() else None,
            groq_api_key=self.groq_api_key,
            gemini_api_key=self.gemini_api_key,
            openrouter_api_key=self.openrouter_api_key,
            ollama_base_url=self.ollama_base_url
        )
        return model, prov

    def get_full_sequence(self) -> List[Tuple[Union[str, BaseChatModel], str]]:
        """Returns the full sequence: [primary_model, *fallback_models]."""
        full_specs = [self.primary_spec] + [f for f in self.fallback_specs if f != self.primary_spec]
        seq = []
        for s in full_specs:
            name = s if isinstance(s, str) else (getattr(s, "model_name", None) or s._llm_type)
            seq.append((s, str(name).lower()))
        return seq

    def build_runnable_with_fallbacks(
        self,
        tools: Optional[Sequence[Any]] = None
    ) -> Optional[Union[BaseChatModel, RunnableWithFallbacks]]:
        """
        Constructs a native LangChain RunnableWithFallbacks object binding the primary
        and all available fallback models.
        """
        resolved_models: List[BaseChatModel] = []
        for spec, _ in self.get_full_sequence():
            m, _ = self._resolve_model(spec)
            if m is not None:
                if tools:
                    m = m.bind_tools(tools)
                resolved_models.append(m)

        if not resolved_models:
            return None
        if len(resolved_models) == 1:
            return resolved_models[0]

        return resolved_models[0].with_fallbacks(
            resolved_models[1:],
            exceptions_to_handle=(Exception,)
        )

    async def execute(
        self,
        messages: List[BaseMessage],
        tools: Optional[Sequence[Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes model invocation using the model fallback middleware:
        Tries primary model, then falls back through fallbackModels upon errors in sequence.
        Returns execution details, active model, fallback status, and error logs.
        """
        sequence = self.get_full_sequence()
        if not sequence:
            return {
                "response": None,
                "provider_used": "local",
                "fallback_active": True,
                "fallback_reason": "Zero-key deterministic local planner requested",
                "cascade_attempted": [],
                "errors": []
            }

        attempted: List[str] = []
        failure_reasons: List[str] = []
        primary_name = sequence[0][1]

        for idx, (spec, name) in enumerate(sequence):
            attempted.append(name)
            is_fallback_attempt = (idx > 0)

            try:
                model, prov_name = self._resolve_model(spec)
            except Exception as e:
                err = f"{name} init error: {str(e).splitlines()[0]}"
                failure_reasons.append(err)
                logger.warning(f"[modelFallbackMiddleware] {err}. Attempting next fallback model...")
                continue

            if model is None:
                err = f"{name}: credentials missing or unconfigured"
                failure_reasons.append(err)
                logger.info(f"[modelFallbackMiddleware] {err}. Attempting next fallback model...")
                continue

            try:
                model_to_call = model.bind_tools(tools) if tools else model
                resp = await model_to_call.ainvoke(messages)

                reason = (
                    f"Primary model '{primary_name}' failed ({'; '.join(failure_reasons)}). Successfully fell back to '{name}'."
                    if is_fallback_attempt else None
                )

                logger.info(
                    f"[modelFallbackMiddleware] Succeeded with model '{name}'. "
                    f"Fallback active: {is_fallback_attempt}"
                )
                return {
                    "response": resp,
                    "provider_used": name,
                    "fallback_active": is_fallback_attempt,
                    "fallback_reason": reason,
                    "cascade_attempted": attempted,
                    "errors": failure_reasons
                }
            except Exception as e:
                err_msg = str(e).splitlines()[0][:140]
                err = f"{name} execution error: {err_msg}"
                failure_reasons.append(err)
                logger.warning(f"[modelFallbackMiddleware] {err}. Attempting next fallback model in sequence...")
                continue

        total_reason = f"All models in fallback middleware exhausted ({'; '.join(failure_reasons)}). Active fallback: local deterministic planner."
        logger.warning(f"[modelFallbackMiddleware] Exhausted all fallback models: {total_reason}")
        return {
            "response": None,
            "provider_used": "local",
            "fallback_active": True,
            "fallback_reason": total_reason,
            "cascade_attempted": attempted,
            "errors": failure_reasons
        }


def modelFallbackMiddleware(
    fallbackModels: Optional[Union[str, Sequence[Union[str, BaseChatModel]]]] = None,
    primary_model: Optional[Union[str, BaseChatModel]] = "groq",
    **kwargs: Any
) -> ModelFallbackMiddleware:
    """
    Middleware factory matching the specification:
    modelFallbackMiddleware(
        fallbackModels: string | AgentLanguageModelLike[]
    ): AgentMiddleware

    Attempts to retry failed model calls with alternative models in sequence.
    When a model call fails, it tries the next model in the fallback list until
    either a call succeeds or all models have been exhausted.
    """
    return ModelFallbackMiddleware(
        fallback_models=fallbackModels,
        primary_model=primary_model,
        **kwargs
    )

# Pythonic snake_case alias
model_fallback_middleware = modelFallbackMiddleware
