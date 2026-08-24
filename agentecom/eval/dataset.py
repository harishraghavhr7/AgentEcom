"""
Golden Evaluation Dataset for Agent Query Retrieval.
Contains realistic queries issued by AI agents with expected target SKUs.
"""

from typing import List, Dict, Any

EVAL_QUERIES: List[Dict[str, Any]] = [
    # 1. Exact SKU & Code Queries (Lexical BM25 strength)
    {
        "query": "SKU-4471",
        "expected_sku": "SKU-4471",
        "category_type": "Exact SKU",
        "description": "Direct SKU lookup from prior cart or recommendation"
    },
    {
        "query": "SONY-WH1000XM5",
        "expected_sku": "SONY-WH1000XM5",
        "category_type": "Exact SKU",
        "description": "Exact product model identifier"
    },
    {
        "query": "PATAG-DWN-882",
        "expected_sku": "PATAG-DWN-882",
        "category_type": "Exact SKU",
        "description": "Brand-prefixed SKU lookup"
    },
    {
        "query": "DELL-U2723QE",
        "expected_sku": "DELL-U2723QE",
        "category_type": "Exact SKU",
        "description": "Hardware monitor model code"
    },

    # 2. Natural Language / Paraphrased Semantic Queries (Dense Vector strength)
    {
        "query": "cozy oversized sweater for freezing winter weather",
        "expected_sku": "SKU-4471",
        "category_type": "Semantic / Paraphrase",
        "description": "Natural language query with synonyms (freezing winter vs cold winter days)"
    },
    {
        "query": "silence and noise reduction over-ear headset with long battery",
        "expected_sku": "SONY-WH1000XM5",
        "category_type": "Semantic / Paraphrase",
        "description": "Descriptive feature ask without exact brand name in front"
    },
    {
        "query": "extreme mountaineering packable winter coat with goose feathers",
        "expected_sku": "PATAG-DWN-882",
        "category_type": "Semantic / Paraphrase",
        "description": "Conceptual description of ultralight down jacket"
    },
    {
        "query": "comfortable computer mouse with quiet clicks for productivity",
        "expected_sku": "LOGI-MX-MST3S",
        "category_type": "Semantic / Paraphrase",
        "description": "User intent description of Logitech MX Master 3S"
    },

    # 3. Specific Feature & Component Queries (Hybrid strength)
    {
        "query": "custom aluminum mechanical keyboard red switches wireless",
        "expected_sku": "KEYCH-Q1-PRO",
        "category_type": "Feature Search",
        "description": "Combined technical specs and form factor"
    },
    {
        "query": "4K IPS Black monitor with 90W USB-C hub",
        "expected_sku": "DELL-U2723QE",
        "category_type": "Feature Search",
        "description": "Exact spec matching for display"
    },
    {
        "query": "high end ergonomic desk chair with posture spinal support",
        "expected_sku": "HERM-AER-CHAIR",
        "category_type": "Feature Search",
        "description": "Ergonomic chair intent with posture keywords"
    },
    {
        "query": "electric gooseneck kettle with precise temperature control matte black",
        "expected_sku": "FELL-STAG-EKG",
        "category_type": "Feature Search",
        "description": "Specialty coffee gear feature search"
    },
    {
        "query": "classic hourglass glass coffee brewer with wooden collar",
        "expected_sku": "CHEMEX-OTT-6C",
        "category_type": "Feature Search",
        "description": "Chemex pour over description"
    },

    # 4. Typo / Fuzzy / Partial Queries (Hybrid strength)
    {
        "query": "ergonmic mesh offce chair",
        "expected_sku": "HERM-AER-CHAIR",
        "category_type": "Typo / Fuzzy",
        "description": "Spelling mistakes in user prompt"
    },
    {
        "query": "corduroy button down shirt green",
        "expected_sku": "SKU-4472",
        "category_type": "Typo / Fuzzy",
        "description": "Attribute phrase without exact product title"
    },
    {
        "query": "airpods pro usb-c noise cancel earbuds",
        "expected_sku": "APPL-AIRPODS-PRO2",
        "category_type": "Typo / Fuzzy",
        "description": "Informal product naming"
    }
]
