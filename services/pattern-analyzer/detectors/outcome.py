"""Outcome needed detector - identifies decisions that need outcome tracking."""
from __future__ import annotations

import os
from typing import List, Dict, Any

from .base import BaseDetector


class OutcomeNeededDetector(BaseDetector):
    """Detects decisions that are old enough to have outcomes but don't."""

    def __init__(self, conn, org_id: str):
        super().__init__(conn, org_id)
        self.min_age_days = int(os.environ.get("OUTCOME_MIN_AGE_DAYS", "30"))
        self.max_age_days = int(os.environ.get("OUTCOME_MAX_AGE_DAYS", "180"))

    def detect(self) -> List[Dict[str, Any]]:
        """Find decisions that need outcome tracking."""
        insights = []

        query = """
            SELECT
                d.decision_id,
                d.title,
                d.what_decided,
                d.decided_at,
                ds.stream_name,
                EXTRACT(DAY FROM (NOW() - d.decided_at)) as days_old,
                COUNT(do.outcome_id) as outcome_count
            FROM decision d
            JOIN decision_stream ds ON d.stream_id = ds.stream_id
            LEFT JOIN decision_outcome do ON d.decision_id = do.decision_id
            WHERE d.org_id = %s
              AND d.status = 'active'
              AND d.decided_at < NOW() - INTERVAL '%s days'
              AND d.decided_at > NOW() - INTERVAL '%s days'
            GROUP BY d.decision_id, d.title, d.what_decided, d.decided_at, ds.stream_name
            HAVING COUNT(do.outcome_id) = 0
            ORDER BY d.decided_at ASC
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (self.org_id, self.min_age_days, self.max_age_days))
            rows = cur.fetchall()

            for row in rows:
                decision_id, title, what_decided, decided_at, stream_name, days_old, outcome_count = row

                # Determine severity based on age
                if days_old > 120:
                    severity = "warning"
                elif days_old > 60:
                    severity = "attention"
                else:
                    severity = "info"

                insights.append(
                    self.create_insight(
                        insight_type="outcome_needed",
                        severity=severity,
                        title=f"Outcome needed: {title}",
                        description=f'The decision "{title}" in {stream_name} was made {int(days_old)} days ago. Consider recording what actually happened and any lessons learned.',
                        decision_ids=[str(decision_id)],
                        evidence={
                            "decision_id": str(decision_id),
                            "title": title,
                            "stream": stream_name,
                            "decided_at": decided_at.isoformat(),
                            "days_old": int(days_old),
                        },
                    )
                )

        self.log(f"Found {len(insights)} decisions needing outcome tracking")
        return insights
