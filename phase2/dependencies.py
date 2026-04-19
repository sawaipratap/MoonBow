from phase2.config import config
from phase2.interfaces.db_reader import DBReader
from phase2.interfaces.db_writer import DBWriter
from phase2.interfaces.skill_loader import SkillLoader
from phase2.interfaces.ref_tool import RefTool


def get_db_reader() -> DBReader:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_db_reader import MockDBReader
        return MockDBReader()
    from mcp.postgresql_mcp.server import read_syllabus
    class MCPDBReaderAdapter(DBReader):
        def read_syllabus(self, course_code: str) -> dict:
            return read_syllabus(course_code)
    return MCPDBReaderAdapter()


def get_db_writer() -> DBWriter:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_db_writer import MockDBWriter
        return MockDBWriter()
    from mcp.postgresql_mcp.server import write_refined_syllabus
    class MCPDBWriterAdapter(DBWriter):
        def write_refined_syllabus(self, syllabus, course_code, evaluation_results):
            return write_refined_syllabus(syllabus.model_dump(), course_code, evaluation_results)
    return MCPDBWriterAdapter()


def get_skill_loader() -> SkillLoader:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_skill_loader import MockSkillLoader
        return MockSkillLoader()
    from mcp.filesystem_mcp.server import read_skill
    class MCPSkillLoaderAdapter(SkillLoader):
        def load(self, skill_name: str) -> str:
            return read_skill(skill_name)
    return MCPSkillLoaderAdapter()


def get_ref_tool() -> RefTool:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_ref_tool import MockRefTool
        return MockRefTool()
    from mcp.reference_database_mcp.server import lookup_benchmark_curriculum, lookup_accreditation_standards
    class MCPRefToolAdapter(RefTool):
        def lookup_benchmark_curriculum(self, domain, level, top_k=3):
            return lookup_benchmark_curriculum(domain, level, top_k)
        def lookup_accreditation_standards(self, domain, level, accreditation_body="NBA"):
            return lookup_accreditation_standards(domain, level, accreditation_body)
    return MCPRefToolAdapter()
