from langgraph.graph import StateGraph, END
from phase2.state import Phase2State
from phase2.nodes.skill_injector import skill_injector_node
from phase2.nodes.syllabus_reader import syllabus_reader_node
from phase2.nodes.level_evaluator import level_evaluator_node
from phase2.nodes.sequence_evaluator import sequence_evaluator_node
from phase2.nodes.hours_evaluator import hours_evaluator_node
from phase2.nodes.relevance_evaluator import relevance_evaluator_node
from phase2.nodes.aggregator import aggregator_node
from phase2.nodes.output_writer import output_writer_node


def _routing_logic(state: Phase2State) -> str:
    if state.phase_status == "passed":
        return "write"
    if state.phase_status == "failed":       # hard failure from syllabus_reader
        return "end_failed"
    return "return_to_phase1"


def _should_run_evaluators(state: Phase2State) -> str:
    """Skip evaluators if syllabus_reader already set a failure."""
    if state.phase_status == "failed":
        return "end_failed"
    return "run"


builder = StateGraph(Phase2State)

# Nodes
builder.add_node("skill_injector", skill_injector_node)
builder.add_node("syllabus_reader", syllabus_reader_node)
builder.add_node("level_evaluator", level_evaluator_node)
builder.add_node("sequence_evaluator", sequence_evaluator_node)
builder.add_node("hours_evaluator", hours_evaluator_node)
builder.add_node("relevance_evaluator", relevance_evaluator_node)
builder.add_node("aggregator", aggregator_node)
builder.add_node("output_writer", output_writer_node)

# Entry
builder.set_entry_point("skill_injector")
builder.add_edge("skill_injector", "syllabus_reader")

# After syllabus_reader: fan-out to all 4 evaluators in parallel
builder.add_edge("syllabus_reader", "level_evaluator")
builder.add_edge("syllabus_reader", "sequence_evaluator")
builder.add_edge("syllabus_reader", "hours_evaluator")
builder.add_edge("syllabus_reader", "relevance_evaluator")

# Fan-in: all 4 evaluators converge at aggregator
builder.add_edge("level_evaluator", "aggregator")
builder.add_edge("sequence_evaluator", "aggregator")
builder.add_edge("hours_evaluator", "aggregator")
builder.add_edge("relevance_evaluator", "aggregator")

# Routing from aggregator
builder.add_conditional_edges(
    "aggregator",
    _routing_logic,
    {
        "write": "output_writer",
        "return_to_phase1": END,   # caller receives compiled_feedback and re-runs Phase 1
        "end_failed": END
    }
)
builder.add_edge("output_writer", END)

phase2_graph = builder.compile()
