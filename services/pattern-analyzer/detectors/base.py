"""Base class for pattern detectors."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from psycopg import Connection

logger = logging.getLogger("pattern-analyzer")


class BaseDetector(ABC):
    """
    Abstract base class for all pattern detectors.
    Each detector analyzes decisions and generates insights.
    """

    def __init__(self, conn: Connection, org_id: str):
        """
        Initialize detector.

        Args:
            conn: Database connection
            org_id: Organization ID to analyze
        """
        self.conn = conn
        self.org_id = org_id

    @abstractmethod
    def detect(self) -> List[Dict[str, Any]]:
        """
        Run detection logic and return list of insights.

        Returns:
            List of insight dictionaries with keys:
                - insight_type: str (revisit_due, assumption_drift, conflict, etc.)
                - severity: str (critical, warning, attention, info)
                - title: str (short summary)
                - description: str (detailed explanation)
                - decision_ids: List[str] (related decisions)
                - evidence: Dict[str, Any] (supporting data)
                - org_id: str (organization)
        """
        pass

    def create_insight(
        self,
        insight_type: str,
        severity: str,
        title: str,
        description: str,
        decision_ids: List[str],
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a standardized insight dictionary.

        Args:
            insight_type: Type of insight
            severity: critical, warning, attention, info
            title: Short summary
            description: Detailed explanation
            decision_ids: List of related decision IDs
            evidence: Supporting data

        Returns:
            Insight dictionary
        """
        return {
            "org_id": self.org_id,
            "insight_type": insight_type,
            "severity": severity,
            "title": title,
            "description": description,
            "decision_ids": decision_ids,
            "evidence": evidence,
            "status": "active",
        }

    def log(self, message: str, level: str = "info"):
        """Log a message with detector context."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"[{self.__class__.__name__}] {message}")
