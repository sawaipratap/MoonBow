import json
import os
from datetime import datetime
from phase1.state import SyllabusDraft
from phase2.interfaces.db_writer import DBWriter
from phase2.config import config


class MockDBWriter(DBWriter):
    """Writes the refined syllabus to a local JSON file in phase2/mock_outputs/."""

    def write_refined_syllabus(
        self,
        syllabus: SyllabusDraft,
        course_code: str,
        evaluation_results: dict
    ) -> str:
        os.makedirs(config.MOCK_OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"refined_syllabus_mock_{course_code}_{timestamp}.json"
        path = os.path.join(config.MOCK_OUTPUT_DIR, filename)

        payload = {
            "course_code": course_code,
            "phase_status": "passed",
            "evaluation_results": evaluation_results,
            "syllabus": syllabus.model_dump()
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        print(f"[MockDBWriter] Refined syllabus written: {filename}")
        return filename
