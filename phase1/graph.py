from langgraph.graph import StateGraph, END
from phase1.state import Phase1State
from phase1.nodes.curriculum_loader import curriculum_loader_node
from phase1.nodes.skill_injector import skill_injector_node
from phase1.nodes.expander import expander_node
from phase1.nodes.gap_critic import gap_critic_node
from phase1.nodes.output_writer import output_writer_node
from phase1.config import config

def increment_iteration(state: Phase1State) -> dict:
    return {"iteration_count": state.iteration_count + 1}

def routing_logic(state: Phase1State) -> str:
    print(f"[router] Evaluating iteration {state.iteration_count}")

    if not state.critic_feedback:
        print("[router] Route: critic missing -> expander")
        return "expander"

    if state.critic_feedback.has_gaps:
        if state.iteration_count >= config.MAX_ITERATIONS:
            print(f"[router] Route: MAX_ITERATIONS ({config.MAX_ITERATIONS}) reached despite gaps -> output_writer")
            return "output_writer"
        else:
            print("[router] Route: gaps found -> expander")
            return "expander"

    print("[router] Route: zero gaps -> output_writer")
    return "output_writer"

# Build Graph
builder = StateGraph(Phase1State)

# Add Nodes
builder.add_node("loader", curriculum_loader_node)
builder.add_node("injector", skill_injector_node)
builder.add_node("expander", expander_node)
builder.add_node("critic", gap_critic_node)
builder.add_node("incrementer", increment_iteration)
builder.add_node("writer", output_writer_node)

# Add Edges
builder.set_entry_point("loader")
builder.add_edge("loader", "injector")
builder.add_edge("injector", "expander")
builder.add_edge("expander", "critic")
builder.add_edge("critic", "incrementer")

# Conditional Routing
builder.add_conditional_edges(
    "incrementer",
    routing_logic,
    {
        "expander": "expander",
        "output_writer": "writer"
    }
)

builder.add_edge("writer", END)

# Compile Graph
phase1_graph = builder.compile()
