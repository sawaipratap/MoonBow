import json
import os
from phase2.interfaces.db_reader import DBReader
from phase2.config import config


class MockDBReader(DBReader):
    """
    Reads Phase 1 output from the local mock_outputs directory.
    Expects filenames in the format: syllabus_mock_{COURSE_CODE}_*.json
    Picks the most recent file if multiple exist.
    """

    def read_syllabus(self, course_code: str) -> dict:
        output_dir = config.PHASE1_OUTPUT_DIR
        matches = [
            f for f in os.listdir(output_dir)
            if f.startswith(f"syllabus_mock_{course_code}") and f.endswith(".json")
        ]
        if not matches:
            raise FileNotFoundError(
                f"MockDBReader: No Phase 1 output found for {course_code} in {output_dir}.\n"
                f"Run Phase 1 first with DEPENDENCY_MODE=mock."
            )
        # Take the most recently modified file
        latest = sorted(
            matches,
            key=lambda f: os.path.getmtime(os.path.join(output_dir, f)),
            reverse=True
        )[0]
        path = os.path.join(output_dir, latest)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[MockDBReader] Reading Phase 1 output: {latest}")
        return {
            "syllabus": data.get("syllabus", data),   # handle both wrapped and flat formats
            "phase_status": data.get("phase_status", "passed"),
            "iteration_count": data.get("iteration_count", 0)
        }
