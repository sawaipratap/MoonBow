import os
from phase1.interfaces.file_reader import FileReader
from phase1.config import config

class MockFileReader(FileReader):
    def read_curriculum(self, file_path: str) -> str:
        if os.path.isabs(file_path) and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        local_path = os.path.join(config.TEST_DATA_DIR, os.path.basename(file_path))
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()
