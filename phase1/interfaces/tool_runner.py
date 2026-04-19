from abc import ABC, abstractmethod

class ToolRunner(ABC):
    @abstractmethod
    def run_similarity_search(self, topics: list[str], top_k: int = 5) -> list[dict]: pass
