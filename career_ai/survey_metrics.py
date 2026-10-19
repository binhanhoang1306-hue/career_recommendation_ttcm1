"""Transparent summaries for optional post-recommendation student surveys."""

import math


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    """Return a two-sided Wilson score interval as percentages."""
    if total <= 0:
        return None

    proportion = successes / total
    z_squared = z * z
    denominator = 1 + z_squared / total
    center = (proportion + z_squared / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / total
            + z_squared / (4 * total * total)
        )
        / denominator
    )
    return round(max(0.0, center - margin) * 100, 1), round(
        min(1.0, center + margin) * 100, 1
    )


def summarize_student_survey(feedbacks: list[dict]) -> dict:
    """Summarize answered survey fields without treating perceptions as accuracy."""
    surveys = [record.get("survey") or {} for record in feedbacks]
    responses = [survey for survey in surveys if survey]
    relevance = [
        survey["relevance"]
        for survey in responses
        if type(survey.get("relevance")) is int
    ]
    usefulness = [
        survey["usefulness"]
        for survey in responses
        if type(survey.get("usefulness")) is int
    ]
    intents = [
        survey["explore_intent"]
        for survey in responses
        if survey.get("explore_intent") in {"yes", "maybe", "no"}
    ]
    relevance_positive_count = sum(score >= 4 for score in relevance)
    usefulness_positive_count = sum(score >= 4 for score in usefulness)
    intent_yes_count = sum(intent == "yes" for intent in intents)

    return {
        "response_count": len(responses),
        "relevance_count": len(relevance),
        "average_relevance": round(sum(relevance) / len(relevance), 2) if relevance else None,
        "relevance_positive_pct": (
            round(relevance_positive_count / len(relevance) * 100, 1)
            if relevance else None
        ),
        "relevance_positive_ci95": _wilson_interval(
            relevance_positive_count, len(relevance)
        ),
        "usefulness_count": len(usefulness),
        "average_usefulness": round(sum(usefulness) / len(usefulness), 2) if usefulness else None,
        "usefulness_positive_pct": (
            round(usefulness_positive_count / len(usefulness) * 100, 1)
            if usefulness else None
        ),
        "usefulness_positive_ci95": _wilson_interval(
            usefulness_positive_count, len(usefulness)
        ),
        "intent_count": len(intents),
        "explore_intent_yes_pct": (
            round(intent_yes_count / len(intents) * 100, 1)
            if intents else None
        ),
        "explore_intent_yes_ci95": _wilson_interval(intent_yes_count, len(intents)),
        "minimum_recommended_sample": 20,
    }
