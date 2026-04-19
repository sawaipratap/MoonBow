from phase2.config import config
from phase2.interfaces.skill_loader import SkillLoader
from phase2.interfaces.db_ops import DBReader, DBWriter
from phase2.interfaces.external_tools import ReferenceDB, CustomToolsRunner


def get_skill_loader() -> SkillLoader:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_skill_loader import MockSkillLoader
        return MockSkillLoader()
    from mcp.filesystem_mcp.server import read_skill
    class MCPSkillLoaderAdapter(SkillLoader):
        def load(self, s): return read_skill(s)
        def list_available_skills(self): return []
    return MCPSkillLoaderAdapter()


def get_db_reader() -> DBReader:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_db_ops import MockDBReader
        return MockDBReader()
    from mcp.postgresql_mcp.server import read_syllabus
    class MCPDBReaderAdapter(DBReader):
        def read_latest_syllabus(self, course_code):
            return read_syllabus(course_code)
    return MCPDBReaderAdapter()


def get_db_writer() -> DBWriter:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_db_ops import MockDBWriter
        return MockDBWriter()
    from mcp.postgresql_mcp.server import write_refined_syllabus
    class MCPDBWriterAdapter(DBWriter):
        def write_refined_syllabus(self, syllabus, course_code, phase_status, evaluator_results):
            return write_refined_syllabus(syllabus.model_dump(), course_code, phase_status, evaluator_results)
    return MCPDBWriterAdapter()


def get_reference_db() -> ReferenceDB:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_external_tools import MockReferenceDB
        return MockReferenceDB()
    from mcp.reference_database_mcp.server import lookup_benchmark
    class MCPReferenceDBAdapter(ReferenceDB):
        def lookup(self, domain, level): return lookup_benchmark(domain, level)
    return MCPReferenceDBAdapter()


def get_custom_tools() -> CustomToolsRunner:
    if config.DEPENDENCY_MODE == "mock":
        from phase2.mocks.mock_external_tools import MockCustomToolsRunner
        return MockCustomToolsRunner()
    from mcp.custom_tools_mcp.server import calculate_credit_hours
    class MCPCustomToolsAdapter(CustomToolsRunner):
        def calculate_credit_hours(self, hours, credit_hours):
            return calculate_credit_hours(hours, credit_hours)
    return MCPCustomToolsAdapter()
