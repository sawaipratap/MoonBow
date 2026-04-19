from langgraph.graph import StateGraph, END
from phase2.state import Phase2State
from phase2.nodes.level_evaluator import level_evaluator_node
from phase2.nodes.sequence_evaluator import sequence_evaluator_node
from phase2.nodes.hours_evaluator import hours_evaluator_node
from phase2.nodes.relevance_evaluator import relevance_evaluator_node
from phase2.nodes.aggregator import aggregator_node


def scatter_node(state: Phase2State) -> dict:
    """
    No-op dispatch node. Its sole purpose is to be the single entry point
    that LangGraph fans out from into all 4 parallel evaluator branches.
    Returns no state changes — it just enables the parallel topology.
    """
    print("[scatter] Dispatching to 4 parallel evaluators...")
    return {}


def build_phase2_graph():
    builder = StateGraph(Phase2State)

    # --- Nodes ---
    builder.add_node("scatter", scatter_node)
    builder.add_node("level_evaluator", level_evaluator_node)
    builder.add_node("sequence_evaluator", sequence_evaluator_node)
    builder.add_node("hours_evaluator", hours_evaluator_node)
    builder.add_node("relevance_evaluator", relevance_evaluator_node)
    builder.add_node("aggregator", aggregator_node)

    # --- Fan-out edges: scatter → all 4 evaluators ---
    # LangGraph runs all nodes fanned-out from a single source in parallel.
    builder.set_entry_point("scatter")
    builder.add_edge("scatter", "level_evaluator")
    builder.add_edge("scatter", "sequence_evaluator")
    builder.add_edge("scatter", "hours_evaluator")
    builder.add_edge("scatter", "relevance_evaluator")

    # --- Fan-in edges: all 4 evaluators → aggregator ---
    # LangGraph waits for ALL incoming edges to complete before executing the fan-in node.
    builder.add_edge("level_evaluator", "aggregator")
    builder.add_edge("sequence_evaluator", "aggregator")
    builder.add_edge("hours_evaluator", "aggregator")
    builder.add_edge("relevance_evaluator", "aggregator")

    builder.add_edge("aggregator", END)

    return builder.compile()


phase2_graph = build_phase2_graph()
