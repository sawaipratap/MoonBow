from phase1.config import config
from phase1.interfaces.file_reader import FileReader
from phase1.interfaces.db_writer import DBWriter
from phase1.interfaces.skill_loader import SkillLoader
from phase1.interfaces.tool_runner import ToolRunner

def get_file_reader() -> FileReader:
    if config.DEPENDENCY_MODE == "mock":
        from phase1.mocks.mock_file_reader import MockFileReader
        return MockFileReader()
    from mcp.filesystem_mcp.server import read_curriculum
    class MCPFileReaderAdapter(FileReader):
        def read_curriculum(self, fp): return read_curriculum(fp)
    return MCPFileReaderAdapter()

def get_db_writer() -> DBWriter:
    if config.DEPENDENCY_MODE == "mock":
        from phase1.mocks.mock_db_writer import MockDBWriter
        return MockDBWriter()
    from mcp.postgresql_mcp.server import write_syllabus, check_syllabus_exists
    class MCPDBWriterAdapter(DBWriter):
        def write_syllabus(self, syllabus, course_code, phase_status, iteration_count): 
            return write_syllabus(syllabus.model_dump(), course_code, phase_status, iteration_count)
        def check_syllabus_exists(self, c): return check_syllabus_exists(c)
    return MCPDBWriterAdapter()

def get_skill_loader() -> SkillLoader:
    if config.DEPENDENCY_MODE == "mock":
        from phase1.mocks.mock_skill_loader import MockSkillLoader
        return MockSkillLoader()
    from mcp.filesystem_mcp.server import read_skill
    class MCPSkillLoaderAdapter(SkillLoader):
        def load(self, s): return read_skill(s)
        def list_available_skills(self): return []
    return MCPSkillLoaderAdapter()

def get_tool_runner() -> ToolRunner:
    if config.DEPENDENCY_MODE == "mock":
        from phase1.mocks.mock_tool_runner import MockToolRunner
        return MockToolRunner()
    raise NotImplementedError("MCPToolRunner not built yet")
