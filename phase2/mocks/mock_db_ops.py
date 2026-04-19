import os
import glob
import json
from phase2.interfaces.db_ops import DBReader, DBWriter
from phase2.config import config
from phase1.state import SyllabusDraft

class MockDBReader(DBReader):
    """
    In mock mode, reads the most recent Phase 1 mock output JSON from disk.
    In production, this is replaced by a PostgreSQL MCP read call.
    """

    def read_latest_syllabus(self, course_code: str) -> SyllabusDraft:
        output_dir = config.PHASE1_MOCK_OUTPUT_DIR
        pattern = os.path.join(output_dir, f"syllabus_mock_{course_code}_*.json")
        matches = sorted(glob.glob(pattern), reverse=True)

        if not matches:
            # Fallback: grab the most recent any-course mock output
            fallback_pattern = os.path.join(output_dir, "syllabus_mock_*.json")
            matches = sorted(glob.glob(fallback_pattern), reverse=True)

        if not matches:
            raise FileNotFoundError(
                f"No Phase 1 mock output found in {output_dir}. "
                "Run phase1/run_phase1.py first to generate a syllabus."
            )

        latest = matches[0]
        print(f"[mock_db_reader] Reading Phase 1 output: {os.path.basename(latest)}")
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Phase 1 mock output wraps the syllabus under "syllabus" key
        syllabus_data = data.get("syllabus", data)
        return SyllabusDraft(**syllabus_data)


class MockDBWriter(DBWriter):
    """
    In mock mode, writes the Phase 2 result to local JSON file in phase2/mock_outputs/.
    In production, replaced by a PostgreSQL MCP write call.
    """

    def write_refined_syllabus(
        self,
        syllabus: SyllabusDraft,
        course_code: str,
        phase_status: str,
        evaluator_results: dict
    ) -> str:
        from datetime import datetime
        os.makedirs(config.MOCK_OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"phase2_result_{course_code}_{timestamp}.json"
        filepath = os.path.join(config.MOCK_OUTPUT_DIR, filename)

        payload = {
            "course_code": course_code,
            "phase_status": phase_status,
            "evaluator_results": evaluator_results,
            "refined_syllabus": syllabus.model_dump()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        print(f"[mock_db_writer] Phase 2 result saved to: {filename}")
        return filename
