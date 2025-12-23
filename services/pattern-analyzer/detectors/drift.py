"""Assumption drift detector using embeddings and LLM verification."""
from __future__ import annotations

import hashlib
import os
from typing import List, Dict, Any, Optional
import httpx
import numpy as np

from .base import BaseDetector


class AssumptionDriftDetector(BaseDetector):
    """Detects when decision assumptions change over time."""

    def __init__(self, conn, org_id: str):
        super().__init__(conn, org_id)
        self.embedding_url = os.environ.get("EMBEDDING_URL", "http://embedding:8080")
        self.inference_url = os.environ.get("INFERENCE_URL", "http://inference:8082")
        self.lookback_months = int(os.environ.get("DRIFT_LOOKBACK_MONTHS", "12"))
        self.similarity_threshold = float(os.environ.get("DRIFT_SIMILARITY_THRESHOLD", "0.85"))

    def detect(self) -> List[Dict[str, Any]]:
        """Detect assumption drift in decision streams."""
        insights = []

        # Get active decision streams
        streams = self._get_streams()

        for stream in streams:
            stream_id = stream["stream_id"]
            stream_name = stream["stream_name"]

            # Get decisions in this stream chronologically
            decisions = self._get_stream_decisions(stream_id)

            if len(decisions) < 2:
                continue

            # Compare newer decisions against older ones
            drift_pairs = self._find_drift_candidates(decisions)

            for old_dec, new_dec in drift_pairs:
                # Use LLM to verify if drift is meaningful
                is_drift, explanation = self._verify_drift(old_dec, new_dec)

                if is_drift:
                    insights.append(
                        self.create_insight(
                            insight_type="assumption_drift",
                            severity="warning",
                            title=f"Assumption may have changed: {new_dec['title']}",
                            description=explanation,
                            decision_ids=[old_dec["decision_id"], new_dec["decision_id"]],
                            evidence={
                                "stream": stream_name,
                                "old_decision": {
                                    "id": old_dec["decision_id"],
                                    "title": old_dec["title"],
                                    "date": old_dec["decided_at"],
                                    "reasoning": old_dec["reasoning"][:200] + "...",
                                },
                                "new_decision": {
                                    "id": new_dec["decision_id"],
                                    "title": new_dec["title"],
                                    "date": new_dec["decided_at"],
                                    "reasoning": new_dec["reasoning"][:200] + "...",
                                },
                                "llm_analysis": explanation,
                            },
                        )
                    )

        self.log(f"Found {len(insights)} assumption drift patterns")
        return insights

    def _get_streams(self) -> List[Dict[str, Any]]:
        """Get all active streams for the org."""
        query = """
            SELECT stream_id, stream_name
            FROM decision_stream
            WHERE org_id = %s AND status = 'active'
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (self.org_id,))
            return [{"stream_id": str(row[0]), "stream_name": row[1]} for row in cur.fetchall()]

    def _get_stream_decisions(self, stream_id: str) -> List[Dict[str, Any]]:
        """Get decisions in a stream ordered by date."""
        query = """
            SELECT
                decision_id,
                title,
                what_decided,
                reasoning,
                constraints_at_time,
                decided_at
            FROM decision
            WHERE org_id = %s
              AND stream_id = %s
              AND status = 'active'
              AND decided_at >= NOW() - INTERVAL '%s months'
            ORDER BY decided_at ASC
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (self.org_id, stream_id, self.lookback_months))
            rows = cur.fetchall()

            decisions = []
            for row in rows:
                decision_id, title, what_decided, reasoning, constraints, decided_at = row
                decisions.append(
                    {
                        "decision_id": str(decision_id),
                        "title": title,
                        "what_decided": what_decided,
                        "reasoning": reasoning or "",
                        "constraints": constraints or {},
                        "decided_at": decided_at.isoformat(),
                    }
                )

            # Get or create embeddings for these decisions
            for decision in decisions:
                decision["embedding"] = self._get_decision_embedding(decision)

            return decisions

    def _get_decision_embedding(self, decision: Dict[str, Any]) -> Optional[List[float]]:
        """Get or create embedding for decision reasoning + constraints."""
        decision_id = decision["decision_id"]

        # Combine text for embedding
        text = f"{decision['what_decided']} {decision['reasoning']}"
        if decision.get("constraints"):
            text += " " + str(decision["constraints"])

        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Check if embedding exists in cache
        query = """
            SELECT embedding::text
            FROM decision_embedding
            WHERE decision_id = %s AND text_hash = %s
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (decision_id, text_hash))
            row = cur.fetchone()

            if row:
                # Parse vector string to list of floats
                return self._parse_vector(row[0])

        # Generate new embedding
        try:
            embedding = self._generate_embedding(text)
            if embedding:
                # Cache it
                self._cache_embedding(decision_id, text_hash, embedding)
                return embedding
        except Exception as e:
            self.log(f"Failed to generate embedding: {e}", "error")
            return None

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Call embedding service to generate embedding."""
        try:
            response = httpx.post(
                f"{self.embedding_url}/v1/embed",
                json={"texts": [text]},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]
        except Exception as e:
            self.log(f"Embedding service error: {e}", "error")
            return None

    def _cache_embedding(self, decision_id: str, text_hash: str, embedding: List[float]):
        """Cache embedding in database."""
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        query = """
            INSERT INTO decision_embedding (decision_id, embedding_model, embedding, text_hash)
            VALUES (%s, %s, %s::vector, %s)
            ON CONFLICT (decision_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    text_hash = EXCLUDED.text_hash,
                    created_at = NOW()
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (decision_id, "all-MiniLM-L6-v2", embedding_str, text_hash))
        self.conn.commit()

    def _parse_vector(self, vector_str: str) -> List[float]:
        """Parse PostgreSQL vector string to list of floats."""
        # Vector format: "[1.2,3.4,5.6]"
        vector_str = vector_str.strip("[]")
        return [float(x) for x in vector_str.split(",")]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_np = np.array(a)
        b_np = np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))

    def _find_drift_candidates(
        self, decisions: List[Dict[str, Any]]
    ) -> List[tuple[Dict[str, Any], Dict[str, Any]]]:
        """Find pairs of decisions that might show assumption drift."""
        candidates = []

        # Compare recent decisions (last 3 months) with older ones
        recent_decisions = [d for d in decisions[-5:]]  # Last 5 decisions
        older_decisions = [d for d in decisions[:-5]]  # Everything before

        for new_dec in recent_decisions:
            if not new_dec.get("embedding"):
                continue

            for old_dec in older_decisions:
                if not old_dec.get("embedding"):
                    continue

                # Calculate similarity
                similarity = self._cosine_similarity(
                    new_dec["embedding"], old_dec["embedding"]
                )

                # High similarity suggests related topic, but we want to check if assumptions changed
                # So we look for pairs that are topically related (>0.5) but not identical (<0.95)
                if 0.5 < similarity < 0.95:
                    candidates.append((old_dec, new_dec))

        return candidates[:5]  # Limit to top 5 candidates to avoid spam

    def _verify_drift(
        self, old_decision: Dict[str, Any], new_decision: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Use LLM to verify if there's meaningful assumption drift."""
        prompt = f"""Analyze these two decisions from the same organization:

OLDER DECISION ({old_decision['decided_at']}):
Title: {old_decision['title']}
What was decided: {old_decision['what_decided']}
Reasoning: {old_decision['reasoning']}

NEWER DECISION ({new_decision['decided_at']}):
Title: {new_decision['title']}
What was decided: {new_decision['what_decided']}
Reasoning: {new_decision['reasoning']}

Question: Did the underlying assumptions or constraints change between these two decisions?

If yes, explain what assumption shifted and whether it appears intentional or unacknowledged.
If no, explain that these decisions are compatible.

Keep your response concise (2-3 sentences)."""

        try:
            # Call inference service in reflection mode
            response = httpx.post(
                f"{self.inference_url}/infer",
                json={
                    "mode": "reflection",
                    "query_text": prompt,
                    "evidence": [],  # No evidence needed for this analysis
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("answer", "")

            # Check if LLM detected drift (heuristic: mentions "change", "shift", "different")
            drift_indicators = ["change", "shift", "different", "drift", "inconsistent", "contradicts"]
            is_drift = any(indicator in answer.lower() for indicator in drift_indicators)

            return is_drift, answer

        except Exception as e:
            self.log(f"LLM verification error: {e}", "error")
            return False, ""
