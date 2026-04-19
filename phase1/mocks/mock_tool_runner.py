from phase1.interfaces.tool_runner import ToolRunner

class MockToolRunner(ToolRunner):
    def run_similarity_search(self, topics: list[str], top_k: int = 5) -> list[dict]:
        return []
