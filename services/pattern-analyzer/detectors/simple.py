"""Simple pattern detectors using SQL queries."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Any

from .base import BaseDetector


class RevisitDueDetector(BaseDetector):
    """Detects decisions that are due for revisit."""

    def detect(self) -> List[Dict[str, Any]]:
        """Find decisions with revisit_date in the past."""
        insights = []

        query = """
            SELECT
                d.decision_id,
                d.title,
                d.what_decided,
                d.revisit_date,
                d.decided_at,
                ds.stream_name,
                EXTRACT(DAY FROM (NOW() - d.revisit_date)) as days_overdue
            FROM decision d
            JOIN decision_stream ds ON d.stream_id = ds.stream_id
            WHERE d.org_id = %s
              AND d.status = 'active'
              AND d.revisit_date IS NOT NULL
              AND d.revisit_date < NOW()
            ORDER BY d.revisit_date ASC
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (self.org_id,))
            rows = cur.fetchall()

            for row in rows:
                decision_id, title, what_decided, revisit_date, decided_at, stream_name, days_overdue = row

                # Determine severity based on how overdue
                if days_overdue > 90:
                    severity = "critical"
                elif days_overdue > 30:
                    severity = "warning"
                else:
                    severity = "attention"

                insights.append(
                    self.create_insight(
                        insight_type="revisit_due",
                        severity=severity,
                        title=f"Decision due for revisit: {title}",
                        description=f'The decision "{title}" in {stream_name} was scheduled for revisit on {revisit_date.strftime("%Y-%m-%d")} ({int(days_overdue)} days ago). It may need re-evaluation given current context.',
                        decision_ids=[str(decision_id)],
                        evidence={
                            "decision_id": str(decision_id),
                            "title": title,
                            "stream": stream_name,
                            "revisit_date": revisit_date.isoformat(),
                            "decided_at": decided_at.isoformat(),
                            "days_overdue": int(days_overdue),
                        },
                    )
                )

        self.log(f"Found {len(insights)} decisions due for revisit")
        return insights


class UnresolvedDissentDetector(BaseDetector):
    """Detects dissent records that remain unresolved."""

    def detect(self) -> List[Dict[str, Any]]:
        """Find open dissent records and group by decision."""
        insights = []

        query = """
            SELECT
                d.decision_id,
                d.title,
                d.what_decided,
                d.decided_at,
                ds.stream_name,
                dr.dissent_id,
                dr.dissenter_name,
                dr.concern,
                dr.reasoning,
                EXTRACT(DAY FROM (NOW() - d.decided_at)) as days_since_decision
            FROM dissent_record dr
            JOIN decision d ON dr.decision_id = d.decision_id
            JOIN decision_stream ds ON d.stream_id = ds.stream_id
            WHERE d.org_id = %s
              AND dr.status = 'open'
              AND d.status = 'active'
            ORDER BY d.decided_at ASC
        """

        # Group dissent by decision
        decision_dissents: Dict[str, Dict[str, Any]] = {}

        with self.conn.cursor() as cur:
            cur.execute(query, (self.org_id,))
            rows = cur.fetchall()

            for row in rows:
                (
                    decision_id,
                    title,
                    what_decided,
                    decided_at,
                    stream_name,
                    dissent_id,
                    dissenter_name,
                    concern,
                    reasoning,
                    days_since_decision,
                ) = row

                decision_id_str = str(decision_id)

                if decision_id_str not in decision_dissents:
                    decision_dissents[decision_id_str] = {
                        "decision_id": decision_id_str,
                        "title": title,
                        "what_decided": what_decided,
                        "stream": stream_name,
                        "decided_at": decided_at,
                        "days_since_decision": int(days_since_decision),
                        "dissents": [],
                    }

                decision_dissents[decision_id_str]["dissents"].append(
                    {
                        "dissent_id": str(dissent_id),
                        "dissenter": dissenter_name,
                        "concern": concern,
                        "reasoning": reasoning,
                    }
                )

        # Create insights for each decision with unresolved dissent
        for decision_id, data in decision_dissents.items():
            num_dissents = len(data["dissents"])
            days_since = data["days_since_decision"]

            # Severity based on age and number of dissents
            if days_since > 60 or num_dissents > 2:
                severity = "warning"
            else:
                severity = "attention"

            dissenter_names = [d["dissenter"] for d in data["dissents"]]
            dissenter_str = ", ".join(dissenter_names) if len(dissenter_names) <= 3 else f"{len(dissenter_names)} people"

            insights.append(
                self.create_insight(
                    insight_type="unresolved_dissent",
                    severity=severity,
                    title=f"Unresolved dissent on: {data['title']}",
                    description=f'{num_dissents} dissenting {"voice" if num_dissents == 1 else "voices"} ({dissenter_str}) on the decision "{data["title"]}" in {data["stream"]} remain unaddressed after {days_since} days. Consider acknowledging or resolving these concerns.',
                    decision_ids=[decision_id],
                    evidence=data,
                )
            )

        self.log(f"Found {len(insights)} decisions with unresolved dissent")
        return insights
