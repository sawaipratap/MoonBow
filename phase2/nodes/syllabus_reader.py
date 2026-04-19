from phase2.state import Phase2State
from phase2.dependencies import get_db_reader
from phase1.state import SyllabusDraft


def syllabus_reader_node(state: Phase2State) -> dict:
    db_reader = get_db_reader()
    record = db_reader.read_syllabus(state.course_code)

    if record.get("phase_status") == "failed":
        return {
            "phase_status": "failed",
            "phase_error": f"Phase 1 produced a failed record for {state.course_code}. Cannot evaluate."
        }

    syllabus_data = record["syllabus"]

    # Handle both raw dict formats: syllabus may be nested under "syllabus" key
    # (from the Phase 1 mock output format) or flat at the top level
    if "course_metadata" not in syllabus_data and "syllabus" in syllabus_data:
        syllabus_data = syllabus_data["syllabus"]

    syllabus_draft = SyllabusDraft(**syllabus_data)
    print(f"[syllabus_reader] Loaded syllabus for {state.course_code}: "
          f"{len(syllabus_draft.topics)} units, {syllabus_draft.total_hours}h total")

    return {
        "syllabus_draft": syllabus_draft,
        "phase1_status": record.get("phase_status", "passed")
    }
