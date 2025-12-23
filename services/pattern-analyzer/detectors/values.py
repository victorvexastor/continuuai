"""Values conflict detector using explicit and extracted organizational values."""
from __future__ import annotations

import os
from typing import List, Dict, Any
import httpx

from .base import BaseDetector


class ValuesConflictDetector(BaseDetector):
    """Detects when decisions conflict with organizational values."""

    def __init__(self, conn, org_id: str):
        super().__init__(conn, org_id)
        self.inference_url = os.environ.get("INFERENCE_URL", "http://inference:8082")
        self.lookback_months = int(os.environ.get("VALUES_LOOKBACK_MONTHS", "6"))

    def detect(self) -> List[Dict[str, Any]]:
        """Detect conflicts with organizational values."""
        insights = []

        # Get active organizational values
        org_values = self._get_org_values()

        if not org_values:
            self.log("No organizational values defined, skipping values conflict detection")
            return insights

        # Get recent decisions
        decisions = self._get_recent_decisions()

        # Check each decision against values
        for decision in decisions:
            for value in org_values:
                conflict = self._check_value_conflict(decision, value)

                if conflict:
                    severity = "critical" if value["strength"] == "must" else "warning"

                    insights.append(
                        self.create_insight(
                            insight_type="values_conflict",
                            severity=severity,
                            title=f"Decision may conflict with value: {value['value_name']}",
                            description=conflict,
                            decision_ids=[decision["decision_id"]],
                            evidence={
                                "value": {
                                    "name": value["value_name"],
                                    "description": value["value_description"],
                                    "strength": value["strength"],
                                    "source": value["source_type"],
                                },
                                "decision": {
                                    "id": decision["decision_id"],
                                    "title": decision["title"],
                                    "what_decided": decision["what_decided"],
                                },
                                "llm_analysis": conflict,
                            },
                        )
                    )

        self.log(f"Found {len(insights)} values conflicts")
        return insights

    def _get_org_values(self) -> List[Dict[str, Any]]:
        """Get active organizational values."""
        query = """
            SELECT
                org_value_id,
                value_name,
                value_description,
                source_type,
                strength
            FROM org_value
            WHERE org_id = %s
              AND status = 'active'
            ORDER BY
                CASE strength
                    WHEN 'must' THEN 1
                    WHEN 'should' THEN 2
                    WHEN 'prefer' THEN 3
                END
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (self.org_id,))
            rows = cur.fetchall()

            return [
                {
                    "org_value_id": str(row[0]),
                    "value_name": row[1],
                    "value_description": row[2],
                    "source_type": row[3],
                    "strength": row[4],
                }
                for row in rows
            ]

    def _get_recent_decisions(self) -> List[Dict[str, Any]]:
        """Get recent active decisions."""
        query = """
            SELECT
                decision_id,
                title,
                what_decided,
                reasoning,
                constraints_at_time
            FROM decision
            WHERE org_id = %s
              AND status = 'active'
              AND decided_at >= NOW() - INTERVAL '%s months'
            ORDER BY decided_at DESC
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (self.org_id, self.lookback_months))
            rows = cur.fetchall()

            return [
                {
                    "decision_id": str(row[0]),
                    "title": row[1],
                    "what_decided": row[2],
                    "reasoning": row[3] or "",
                    "constraints": row[4] or {},
                }
                for row in rows
            ]

    def _check_value_conflict(
        self, decision: Dict[str, Any], value: Dict[str, Any]
    ) -> str | None:
        """Use LLM to check if decision conflicts with organizational value."""
        strength_text = {
            "must": "absolutely required",
            "should": "strongly preferred",
            "prefer": "generally preferred",
        }

        prompt = f"""Analyze if this decision conflicts with an organizational value:

ORGANIZATIONAL VALUE ({strength_text[value['strength']]}):
{value['value_name']}: {value['value_description']}

DECISION:
Title: {decision['title']}
What was decided: {decision['what_decided']}
Reasoning: {decision['reasoning']}
Constraints: {decision['constraints']}

Question: Does this decision conflict with or violate the stated organizational value?

If yes, explain the specific conflict clearly and concisely.
If no, respond with "COMPATIBLE" and explain how it aligns or is neutral.

Keep response to 2-3 sentences."""

        try:
            response = httpx.post(
                f"{self.inference_url}/infer",
                json={
                    "mode": "reflection",
                    "query_text": prompt,
                    "evidence": [],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("answer", "")

            # If response indicates compatibility, no conflict
            if "COMPATIBLE" in answer.upper() or "does not conflict" in answer.lower():
                return None

            # Otherwise, return the explanation
            return answer

        except Exception as e:
            self.log(f"LLM verification error: {e}", "error")
            return None
