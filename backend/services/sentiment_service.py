"""Sentiment analysis service using VADER."""
from typing import Optional

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from backend.utils import db

_analyzer = SentimentIntensityAnalyzer()


async def analyze_and_store_sentiment(grievance_id: str, complaint_text: Optional[str]) -> float:
    """
    Run VADER sentiment analysis on the grievance text and persist the score.

    Args:
        grievance_id: Identifier of the grievance.
        complaint_text: Free-text complaint description.

    Returns:
        The computed compound sentiment score (-1.0 to 1.0).
    """
    text = (complaint_text or "").strip()
    scores = _analyzer.polarity_scores(text)
    compound_score = round(float(scores.get("compound", 0.0)), 2)

    existing = await db.fetch_one(
        "SELECT sentiment_id FROM sentiment_analysis WHERE grievance_id = $1",
        grievance_id,
    )

    if existing:
        await db.execute(
            """
            UPDATE sentiment_analysis
            SET compound_score = $1, analyzed_at = CURRENT_TIMESTAMP
            WHERE grievance_id = $2
            """,
            compound_score,
            grievance_id,
        )
    else:
        await db.execute(
            "INSERT INTO sentiment_analysis (grievance_id, compound_score) VALUES ($1, $2)",
            grievance_id,
            compound_score,
        )

    return compound_score
