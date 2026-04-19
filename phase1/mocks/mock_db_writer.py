import os
import json
from datetime import datetime
from phase1.interfaces.db_writer import DBWriter
from phase1.state import SyllabusDraft
from phase1.config import config

class MockDBWriter(DBWriter):
    def __init__(self):
        os.makedirs(config.MOCK_OUTPUT_DIR, exist_ok=True)

    def write_syllabus(self, syllabus: SyllabusDraft, course_code: str, phase_status: str, iteration_count: int) -> str:
        record_id = f"mock_{course_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output = {
            "record_id": record_id, "course_code": course_code, 
            "phase_status": phase_status, "iteration_count": iteration_count,
            "syllabus": syllabus.model_dump()
        }
        with open(os.path.join(config.MOCK_OUTPUT_DIR, f"syllabus_{record_id}.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        return record_id

    def check_syllabus_exists(self, course_code: str) -> bool:
        if not os.path.exists(config.MOCK_OUTPUT_DIR): return False
        return any(course_code in f for f in os.listdir(config.MOCK_OUTPUT_DIR))
