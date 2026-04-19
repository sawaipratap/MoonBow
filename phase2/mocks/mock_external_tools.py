from phase2.interfaces.external_tools import ReferenceDB, CustomToolsRunner
from phase2.config import config

class MockReferenceDB(ReferenceDB):
    """
    Returns a static benchmark description for any domain/level pair.
    In production, replaced by a lookup against the Reference Database MCP.
    """

    # Minimal benchmark content per domain to give the LLM something concrete.
    DOMAIN_BENCHMARKS = {
        "Computer Science": """
IEEE/ACM Computing Curricula 2023 benchmark for CS at undergraduate level:
- Core areas: Algorithms, Data Structures, Computer Organization, Operating Systems,
  Programming Languages, Software Engineering, Networks, AI/ML, Databases, Security.
- Industry relevance: Cloud computing, DevOps, API design now mandatory in modern CS curricula.
- Typical total lecture hours for a 3-credit course: 42–45 hours.
""",
        "Electrical Engineering": """
IEEE model curriculum for EE undergraduate:
- Core areas: Circuit Analysis, Signals & Systems, Electromagnetics, Power Systems,
  Control Systems, Digital Electronics, Embedded Systems.
- Typical lecture hours for 3-credit: 42–45 hours.
""",
        "Mathematics": """
MAA/AMS undergraduate mathematics standards:
- Core: Calculus, Linear Algebra, Differential Equations, Probability, Discrete Math.
- Graduate: Real Analysis, Abstract Algebra, Topology, Numerical Methods.
- Typical hours: 42–45 lecture hours for 3-credit.
""",
        "DEFAULT": """
General accreditation standard (NBA/NAAC India):
- A 3-credit course is expected to deliver 40–45 contact hours.
- Topics should be sequenced from foundational to advanced.
- All major units should map to at least one measurable Course Outcome.
- Content should reflect current industry or research practice, not solely historical approaches.
"""
    }

    def lookup(self, domain: str, level: str) -> str:
        content = self.DOMAIN_BENCHMARKS.get(domain, self.DOMAIN_BENCHMARKS["DEFAULT"])
        print(f"[mock_reference_db] Lookup: domain='{domain}', level='{level}'")
        return content.strip()


class MockCustomToolsRunner(CustomToolsRunner):
    """
    Implements credit-hour arithmetic deterministically.
    In production, this delegates to the Custom Tools MCP server.
    The tolerance boundary is driven by HOURS_TOLERANCE_PERCENT in config.
    """

    def calculate_credit_hours(self, subtopic_hours: list[float], stated_credit_hours: int) -> dict:
        # Standard conversion: 1 credit hour → 15 lecture hours (50-min sessions per semester)
        expected_lecture_hours = stated_credit_hours * 15
        total_hours = sum(subtopic_hours)
        delta = total_hours - expected_lecture_hours
        tolerance = expected_lecture_hours * (config.HOURS_TOLERANCE_PERCENT / 100.0)
        within_tolerance = abs(delta) <= tolerance

        print(
            f"[mock_custom_tools] Hours: total={total_hours:.1f}, "
            f"expected={expected_lecture_hours}, delta={delta:+.1f}, "
            f"within_tolerance={within_tolerance}"
        )

        return {
            "total_hours": total_hours,
            "expected_hours": expected_lecture_hours,
            "delta": delta,
            "within_tolerance": within_tolerance,
            "tolerance_threshold": tolerance
        }
