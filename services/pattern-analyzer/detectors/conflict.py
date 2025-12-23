"""Decision conflict detector using graph + LLM."""
from __future__ import annotations

import hashlib
import os
from typing import List, Dict, Any, Optional
import httpx
import numpy as np

from .base import BaseDetector


class DecisionConflictDetector(BaseDetector):
    """Detects conflicting decisions using graph analysis and LLM verification."""

    def __init__(self, conn, org_id: str):
        super().__init__(conn, org_id)
        self.embedding_url = os.environ.get("EMBEDDING_URL", "http://embedding:8080")
        self.inference_url = os.environ.get("INFERENCE_URL", "http://inference:8082")
        self.conflict_threshold = float(os.environ.get("CONFLICT_SIMILARITY_THRESHOLD", "0.75"))
        self.lookback_months = int(os.environ.get("CONFLICT_LOOKBACK_MONTHS", "12"))

    def detect(self) -> List[Dict[str, Any]]:
        """Detect decision conflicts."""
        insights = []

        # 1. Check for explicit contradicts edges in graph
        explicit_conflicts = self._find_explicit_conflicts()
        insights.extend(explicit_conflicts)

        # 2. Find potential conflicts using embedding similarity
        similarity_conflicts = self._find_similarity_conflicts()
        insights.extend(similarity_conflicts)

        self.log(f"Found {len(insights)} decision conflicts")
        return insights

    def _find_explicit_conflicts(self) -> List[Dict[str, Any]]:
        """Find decisions with explicit 'contradicts' edges in the graph."""
        insights = []

        query = """
            SELECT
                d1.decision_id as decision_1_id,
                d1.title as decision_1_title,
                d1.what_decided as decision_1_what,
                d2.decision_id as decision_2_id,
                d2.title as decision_2_title,
                d2.what_decided as decision_2_what,
                ge.properties
            FROM graph_edge ge
            JOIN graph_node gn1 ON ge.from_node_id = gn1.node_id
            JOIN graph_node gn2 ON ge.to_node_id = gn2.node_id
            JOIN decision d1 ON gn1.decision_id = d1.decision_id
            JOIN decision d2 ON gn2.decision_id = d2.decision_id
            WHERE ge.org_id = %s
              AND ge.edge_type = 'contradicts'
              AND d1.status = 'active'
              AND d2.status = 'active'
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (self.org_id,))
            rows = cur.fetchall()

            for row in rows:
                dec1_id, dec1_title, dec1_what, dec2_id, dec2_title, dec2_what, properties = row

                insights.append(
                    self.create_insight(
                        insight_type="conflict",
                        severity="critical",
                        title=f"Explicit conflict: {dec1_title} vs {dec2_title}",
                        description=f'Decisions "{dec1_title}" and "{dec2_title}" have been identified as contradictory. Both are currently active, which may create confusion or policy conflicts.',
                        decision_ids=[str(dec1_id), str(dec2_id)],
                        evidence={
                            "conflict_type": "explicit",
                            "decision_1": {
                                "id": str(dec1_id),
                                "title": dec1_title,
                                "what_decided": dec1_what,
                            },
                            "decision_2": {
                                "id": str(dec2_id),
                                "title": dec2_title,
                                "what_decided": dec2_what,
                            },
                            "graph_properties": properties,
                        },
                    )
                )

        return insights

    def _find_similarity_conflicts(self) -> List[Dict[str, Any]]:
        """Find potential conflicts using embedding similarity + LLM verification."""
        insights = []

        # Get recent active decisions
        decisions = self._get_recent_decisions()

        if len(decisions) < 2:
            return insights

        # Ensure all decisions have embeddings
        for decision in decisions:
            decision["embedding"] = self._get_decision_embedding(decision)

        # Find high-similarity pairs (potentially related/conflicting)
        conflict_candidates = self._find_conflict_candidates(decisions)

        # Verify with LLM
        for dec1, dec2, similarity in conflict_candidates:
            is_conflict, explanation = self._verify_conflict(dec1, dec2)

            if is_conflict:
                insights.append(
                    self.create_insight(
                        insight_type="conflict",
                        severity="warning",
                        title=f"Potential conflict: {dec1['title']} vs {dec2['title']}",
                        description=explanation,
                        decision_ids=[dec1["decision_id"], dec2["decision_id"]],
                        evidence={
                            "conflict_type": "semantic",
                            "similarity_score": similarity,
                            "decision_1": {
                                "id": dec1["decision_id"],
                                "title": dec1["title"],
                                "what_decided": dec1["what_decided"],
                            },
                            "decision_2": {
                                "id": dec2["decision_id"],
                                "title": dec2["title"],
                                "what_decided": dec2["what_decided"],
                            },
                            "llm_analysis": explanation,
                        },
                    )
                )

        return insights

    def _get_recent_decisions(self) -> List[Dict[str, Any]]:
        """Get active decisions from recent months."""
        query = """
            SELECT
                decision_id,
                title,
                what_decided,
                reasoning,
                decided_at
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
                    "decided_at": row[4].isoformat(),
                }
                for row in rows
            ]

    def _get_decision_embedding(self, decision: Dict[str, Any]) -> Optional[List[float]]:
        """Get or create embedding for decision."""
        decision_id = decision["decision_id"]

        # Combine text
        text = f"{decision['what_decided']} {decision['reasoning']}"
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Check cache
        query = """
            SELECT embedding::text
            FROM decision_embedding
            WHERE decision_id = %s AND text_hash = %s
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (decision_id, text_hash))
            row = cur.fetchone()

            if row:
                return self._parse_vector(row[0])

        # Generate new
        try:
            embedding = self._generate_embedding(text)
            if embedding:
                self._cache_embedding(decision_id, text_hash, embedding)
                return embedding
        except Exception as e:
            self.log(f"Failed to generate embedding: {e}", "error")
            return None

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Call embedding service."""
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
        """Cache embedding."""
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
        """Parse PostgreSQL vector."""
        vector_str = vector_str.strip("[]")
        return [float(x) for x in vector_str.split(",")]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity."""
        a_np = np.array(a)
        b_np = np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))

    def _find_conflict_candidates(
        self, decisions: List[Dict[str, Any]]
    ) -> List[tuple[Dict[str, Any], Dict[str, Any], float]]:
        """Find pairs of decisions with high similarity (potential conflicts)."""
        candidates = []

        for i, dec1 in enumerate(decisions):
            if not dec1.get("embedding"):
                continue

            for dec2 in decisions[i + 1 :]:
                if not dec2.get("embedding"):
                    continue

                similarity = self._cosine_similarity(dec1["embedding"], dec2["embedding"])

                # High similarity suggests related topics - check for conflict
                if similarity >= self.conflict_threshold:
                    candidates.append((dec1, dec2, similarity))

        # Sort by similarity (highest first) and limit
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[:10]

    def _verify_conflict(
        self, dec1: Dict[str, Any], dec2: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Use LLM to verify if decisions conflict."""
        prompt = f"""Analyze these two decisions from the same organization:

DECISION 1:
Title: {dec1['title']}
What was decided: {dec1['what_decided']}
Reasoning: {dec1['reasoning']}

DECISION 2:
Title: {dec2['title']}
What was decided: {dec2['what_decided']}
Reasoning: {dec2['reasoning']}

Question: Do these decisions conflict or contradict each other?

If yes, explain the specific conflict and potential consequences.
If no, explain how they are compatible or complementary.

Be concise (2-3 sentences)."""

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

            # Detect conflict indicators
            conflict_indicators = [
                "conflict",
                "contradict",
                "incompatible",
                "opposite",
                "inconsistent",
                "oppose",
            ]
            is_conflict = any(indicator in answer.lower() for indicator in conflict_indicators)

            return is_conflict, answer

        except Exception as e:
            self.log(f"LLM verification error: {e}", "error")
            return False, ""
