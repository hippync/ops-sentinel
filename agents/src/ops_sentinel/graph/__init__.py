"""LangGraph orchestration and pipeline state.

Graph topology enforces the core safety invariant structurally: there is no edge
from worker to executor. Every path traverses validator and approval. This is a
property of the graph, not a convention — asserted in tests/integration.
"""
