from abc import ABC, abstractmethod

class FileReader(ABC):
    @abstractmethod
    def read_curriculum(self, file_path: str) -> str: pass
