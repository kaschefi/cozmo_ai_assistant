# backend/test/digital/routers/__init__.py
"""
Routers benchmarking package for evaluating router architectures (WP2 Experiment):

LLM Models (test/digital/routers/models/llm/):
1. Baseline Monolithic LLM (baseline.py)
2. Production Two-Layer LLM (two_layer.py)

LAYA Models (test/digital/routers/models/laya/):
3. Single-Layer Monolithic LAYA (single_layer.py)
4. Two-Layer LAYA (two_layer.py)
5. Single-Layer LAYA with Top-K Tool RAG (single_layer_topk.py)
6. Two-Layer LAYA with Top-K Tool RAG (two_layer_topk.py)
"""

