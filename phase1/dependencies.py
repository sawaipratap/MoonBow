from phase1.config import config
from phase1.interfaces.file_reader import FileReader
from phase1.interfaces.db_writer import DBWriter
from phase1.interfaces.skill_loader import SkillLoader
from phase1.interfaces.tool_runner import ToolRunner

def get_file_reader() -> FileReader:
    from mcp.filesystem_mcp.server import read_curriculum
    class MCPFileReaderAdapter(FileReader):
        def read_curriculum(self, fp): return read_curriculum(fp)
    return MCPFileReaderAdapter()

def get_db_writer() -> DBWriter:
    from mcp.postgresql_mcp.server import write_syllabus, check_syllabus_exists
    class MCPDBWriterAdapter(DBWriter):
        def write_syllabus(self, syllabus, course_code, phase_status, iteration_count): 
            return write_syllabus(syllabus.model_dump(), course_code, phase_status, iteration_count)
        def check_syllabus_exists(self, c): return check_syllabus_exists(c)
    return MCPDBWriterAdapter()

def get_skill_loader() -> SkillLoader:
    from mcp.filesystem_mcp.server import read_skill
    class MCPSkillLoaderAdapter(SkillLoader):
        def load(self, s): return read_skill(s)
        def list_available_skills(self): return []
    return MCPSkillLoaderAdapter()

def get_tool_runner() -> ToolRunner:
    # Phase 1 similarity search (Qdrant) not fully ported to MCP yet
    raise NotImplementedError("MCPToolRunner not built yet")
