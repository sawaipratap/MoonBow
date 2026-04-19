from phase2.interfaces.ref_tool import RefTool


class MockRefTool(RefTool):
    """
    Returns stub reference data so the Relevance Evaluator node can still
    run and produce an output during development, even before the Reference DB
    is populated with real accreditation standards and benchmark curricula.

    The stub returns a minimal result that will cause the Relevance Evaluator
    to produce a passing evaluation with a neutral score, not a skipped one.
    This lets you test the full graph flow without reference data.
    """

    def lookup_benchmark_curriculum(self, domain: str, level: str, top_k: int = 3) -> dict:
        print(f"[MockRefTool] lookup_benchmark_curriculum called for {domain}/{level} — returning stub.")
        return {
            "domain": domain,
            "level": level,
            "benchmark_sources": [],
            "consensus_topics": [],   # empty = no missing topics flagged
            "rarely_included": []
        }

    def lookup_accreditation_standards(
        self, domain: str, level: str, accreditation_body: str = "NBA"
    ) -> dict:
        print(f"[MockRefTool] lookup_accreditation_standards called for {domain}/{level}/{accreditation_body} — returning stub.")
        return {
            "domain": domain,
            "level": level,
            "accreditation_body": accreditation_body,
            "mandatory_topics": [],   # empty = no mandatory topics will fail
            "recommended_topics": [],
            "credit_hour_norms": {}
        }
