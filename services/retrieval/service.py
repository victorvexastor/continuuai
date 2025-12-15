from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import math
import psycopg
from psycopg.rows import dict_row


@dataclass
class RetrievalConfig:
    seed_k: int = 40                 # initial top-k from vector/lexical
    hop_depth: int = 2               # 1-2 is usually plenty
    hop_fanout: int = 80             # limit neighbors per hop to control blow-up
    final_k: int = 12                # return top spans
    alpha_vec: float = 0.55
    beta_bm25: float = 0.25
    gamma_graph: float = 0.15
    delta_recency: float = 0.05
    recency_halflife_days: float = 45.0
    use_mmr: bool = True             # enable MMR diversity selection
    mmr_lambda: float = 0.7          # higher favors relevance, lower favors diversity
    mmr_pool: int = 100              # consider top-N candidates before MMR subset
    bonus_decision: float = 1.2      # legacy per-type knobs (kept for compat)
    bonus_outcome: float = 1.1
    bonus_assumption: float = 1.05
    bonus_map: Optional[Dict[str, float]] = None  # overrides legacy knobs when provided


def _recency_bonus(ts: datetime, halflife_days: float) -> float:
    now = datetime.now(timezone.utc)
    age_days = max(0.0, (now - ts).total_seconds() / 86400.0)
    # exponential decay, returns (0,1]
    return math.exp(-math.log(2) * age_days / max(1e-6, halflife_days))


def _safe_normalize(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    vmin = min(values.values())
    vmax = max(values.values())
    if abs(vmax - vmin) < 1e-9:
        return {k: 1.0 for k in values}
    return {k: (v - vmin) / (vmax - vmin) for k, v in values.items()}


class RetrievalService:
    def __init__(self, dsn: str, cfg: Optional[RetrievalConfig] = None):
        self.dsn = dsn
        self.cfg = cfg or RetrievalConfig()

    def retrieve(
        self,
        org_id: str,
        query_text: str,
        query_embedding: Sequence[float],
        user_id: str = "system",
        acl_groups: Sequence[str] = (),
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Returns top evidence spans after:
        seed -> graph expand -> hybrid score -> policy filter.
        """
        now = now or datetime.now(timezone.utc)

        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # 1) seed spans (vector + lexical)
                seed_spans = self._seed_spans(cur, org_id, query_text, query_embedding)

                # 2) derive seed nodes from spans (via edge_evidence)
                seed_node_ids = self._seed_nodes_from_spans(cur, org_id, [s["id"] for s in seed_spans])

                # 3) expand neighborhood to collect candidate nodes
                expanded_node_ids = self._expand_nodes(cur, org_id, seed_node_ids)

                # 4) collect candidate spans from:
                #    - original seed spans
                #    - spans attached to edges among expanded nodes
                candidate_span_ids = self._candidate_spans(
                    cur, org_id, 
                    seed_span_ids=[s["id"] for s in seed_spans], 
                    node_ids=expanded_node_ids
                )

                # 5) fetch features for candidate spans (vector sim, bm25-ish, recency, graph stats)
                features = self._span_features(
                    cur, org_id, query_text, query_embedding, 
                    candidate_span_ids, expanded_node_ids
                )

                # 6) policy filter (org-level only for now; extend with ACL later)
                allowed_ids = self._policy_filter(cur, org_id, user_id, acl_groups, list(features.keys()), now)

                # 7) score + rank
                ranked = self._score_and_rank(features, allowed_ids)

                # Optional MMR selection for diversity on embedding space
                if self.cfg.use_mmr:
                    # pool is top mmr_pool from ranked
                    pool_ids = [sid for sid, _ in ranked[: self.cfg.mmr_pool]]
                    embed_map = self._span_embeddings(cur, pool_ids)
                    top_ids = self._mmr_select(
                        query_embedding=query_embedding,
                        ranked=ranked,
                        embed_map=embed_map,
                        k=self.cfg.final_k,
                        lam=self.cfg.mmr_lambda,
                    )
                else:
                    top_ids = [sid for sid, _ in ranked[: self.cfg.final_k]]

                # 8) hydrate and return top spans
                spans = self._hydrate_spans(cur, org_id, top_ids)

        return {
            "org_id": org_id,
            "query": query_text,
            "top_k": self.cfg.final_k,
            "results": spans,
            "debug": {
                "seed_spans": len(seed_spans),
                "seed_nodes": len(seed_node_ids),
                "expanded_nodes_count": len(expanded_node_ids),
                "candidate_spans_count": len(candidate_span_ids),
                "allowed_spans_count": len(allowed_ids),
                "returned": len(spans),
                "mmr": {"enabled": self.cfg.use_mmr, "lambda": self.cfg.mmr_lambda, "pool": self.cfg.mmr_pool}
            },
        }

    # ----------------------------- SQL steps -----------------------------

    def _seed_spans(self, cur, org_id: str, query_text: str, query_embedding: Sequence[float]) -> List[Dict[str, Any]]:
        """
        Seed using pgvector similarity + optional lexical.
        Requires: evidence_embedding.embedding vector + pgvector extension.
        """
        # Vector seed
        cur.execute(
            """
            SELECT 
                ee.evidence_span_id as id, 
                es.created_at,
                1 - (ee.embedding <=> %s::vector) AS vec_sim
            FROM evidence_embedding ee
            JOIN evidence_span es ON ee.evidence_span_id = es.evidence_span_id
            WHERE es.org_id = %s
            ORDER BY ee.embedding <=> %s::vector
            LIMIT %s
            """,
            (list(query_embedding), org_id, list(query_embedding), self.cfg.seed_k),
        )
        vec_rows = cur.fetchall()

        # Lexical seed via BM25/ts_rank on artifact_text.fts_en using websearch_to_tsquery
        cur.execute(
            """
            SELECT 
                es.evidence_span_id as id, 
                es.created_at,
                ts_rank(at.fts_en, websearch_to_tsquery('english', %s)) as lex_rank
            FROM evidence_span es
            JOIN artifact_text at ON es.artifact_text_id = at.artifact_text_id
            WHERE es.org_id = %s
              AND at.fts_en @@ websearch_to_tsquery('english', %s)
            ORDER BY lex_rank DESC
            LIMIT %s
            """,
            (query_text, org_id, query_text, max(10, self.cfg.seed_k // 4)),
        )
        lex_rows = cur.fetchall()

        # Merge unique by id
        by_id: Dict[str, Dict[str, Any]] = {}
        for r in vec_rows:
            by_id[str(r["id"])] = {
                "id": str(r["id"]), 
                "created_at": r["created_at"], 
                "vec_sim": float(r["vec_sim"]), 
                "lex": 0.0
            }
        for r in lex_rows:
            sid = str(r["id"])
            by_id.setdefault(sid, {
                "id": sid, 
                "created_at": r["created_at"], 
                "vec_sim": 0.0, 
                "lex": 0.0
            })
            by_id[sid]["lex"] = max(by_id[sid]["lex"], float(r["lex_rank"]))

        return list(by_id.values())

    def _seed_nodes_from_spans(self, cur, org_id: str, span_ids: List[str]) -> List[str]:
        if not span_ids:
            return []

        # Prefer span_node if present
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables 
              WHERE table_schema='public' AND table_name='span_node'
            ) AS has_span_node;
            """
        )
        has_span_node = bool(cur.fetchone()["has_span_node"])
        if has_span_node:
            cur.execute(
                """
                SELECT DISTINCT node_id::text AS node_id
                FROM span_node
                WHERE org_id = %s
                  AND evidence_span_id = ANY(%s)
                """,
                (org_id, span_ids),
            )
            rows = cur.fetchall()
            if rows:
                return [str(r["node_id"]) for r in rows]

        # Fallback: infer nodes via edge_evidence -> graph_edge
        cur.execute(
            """
            SELECT DISTINCT ge.src_node_id::text AS node_id
            FROM edge_evidence ee
            JOIN graph_edge ge ON ge.edge_id = ee.edge_id
            WHERE ge.org_id = %s
              AND ee.evidence_span_id = ANY(%s)
            UNION
            SELECT DISTINCT ge.dst_node_id::text AS node_id
            FROM edge_evidence ee
            JOIN graph_edge ge ON ge.edge_id = ee.edge_id
            WHERE ge.org_id = %s
              AND ee.evidence_span_id = ANY(%s)
            """,
            (org_id, span_ids, org_id, span_ids),
        )
        rows = cur.fetchall()
        return [str(r["node_id"]) for r in rows]

    def _expand_nodes(self, cur, org_id: str, seed_node_ids: List[str]) -> List[str]:
        if not seed_node_ids:
            return []

        visited = set(seed_node_ids)
        frontier = list(seed_node_ids)

        for _hop in range(self.cfg.hop_depth):
            if not frontier:
                break
            
            # Outgoing edges
            cur.execute(
                """
                SELECT DISTINCT dst_node_id::text AS node_id
                FROM graph_edge
                WHERE org_id = %s
                  AND src_node_id = ANY(%s)
                ORDER BY node_id
                LIMIT %s
                """,
                (org_id, frontier, self.cfg.hop_fanout),
            )
            out_rows = cur.fetchall()

            # Incoming edges
            cur.execute(
                """
                SELECT DISTINCT src_node_id::text AS node_id
                FROM graph_edge
                WHERE org_id = %s
                  AND dst_node_id = ANY(%s)
                ORDER BY node_id
                LIMIT %s
                """,
                (org_id, frontier, self.cfg.hop_fanout),
            )
            in_rows = cur.fetchall()

            next_nodes = [str(r["node_id"]) for r in (out_rows + in_rows)]
            new_frontier = []
            for nid in next_nodes:
                if nid not in visited:
                    visited.add(nid)
                    new_frontier.append(nid)
            frontier = new_frontier

        return list(visited)

    def _candidate_spans(self, cur, org_id: str, seed_span_ids: List[str], node_ids: List[str]) -> List[str]:
        ids = set(seed_span_ids)

        if not node_ids:
            return list(ids)

        # Spans supporting edges that touch expanded nodes
        cur.execute(
            """
            SELECT DISTINCT ee.evidence_span_id::text AS id
            FROM graph_edge ge
            JOIN edge_evidence ee ON ee.edge_id = ge.edge_id
            WHERE ge.org_id = %s
              AND (ge.src_node_id = ANY(%s) OR ge.dst_node_id = ANY(%s))
            LIMIT 5000
            """,
            (org_id, node_ids, node_ids),
        )
        for r in cur.fetchall():
            ids.add(str(r["id"]))

        return list(ids)

    def _span_features(
        self,
        cur,
        org_id: str,
        query_text: str,
        query_embedding: Sequence[float],
        span_ids: List[str],
        expanded_node_ids: List[str],
    ) -> Dict[str, Dict[str, float]]:
        if not span_ids:
            return {}

        # vec_sim + created_at
        cur.execute(
            """
            SELECT 
                ee.evidence_span_id::text as id,
                es.created_at,
                1 - (ee.embedding <=> %s::vector) AS vec_sim
            FROM evidence_embedding ee
            JOIN evidence_span es ON ee.evidence_span_id = es.evidence_span_id
            WHERE es.org_id = %s
              AND es.evidence_span_id = ANY(%s)
            """,
            (list(query_embedding), org_id, span_ids),
        )
        rows = cur.fetchall()

        # lexical BM25 for candidates using websearch_to_tsquery
        cur.execute(
            """
            SELECT 
                es.evidence_span_id::text as id,
                ts_rank(at.fts_en, websearch_to_tsquery('english', %s)) as lex_rank
            FROM evidence_span es
            JOIN artifact_text at ON es.artifact_text_id = at.artifact_text_id
            WHERE es.org_id = %s
              AND es.evidence_span_id = ANY(%s)
            """,
            (query_text, org_id, span_ids),
        )
        lex_rows = cur.fetchall()
        lex_map = {str(r["id"]): float(r["lex_rank"]) for r in lex_rows}

        # graph_bonus with optional per-type map: fetch edge rows and compute in Python
        cur.execute(
            """
            SELECT 
                ee.evidence_span_id::text AS id,
                ns.node_type AS src_type,
                nd.node_type AS dst_type,
                (COALESCE(ee.confidence, 0.5) * COALESCE(ge.weight, 1.0))::float AS strength
            FROM edge_evidence ee
            JOIN graph_edge ge ON ge.edge_id = ee.edge_id
            JOIN graph_node ns ON ns.node_id = ge.src_node_id
            JOIN graph_node nd ON nd.node_id = ge.dst_node_id
            WHERE ge.org_id = %s
              AND ee.evidence_span_id = ANY(%s)
              AND (ge.src_node_id = ANY(%s) OR ge.dst_node_id = ANY(%s))
            """,
            (org_id, span_ids, expanded_node_ids, expanded_node_ids),
        )
        rows_edges = cur.fetchall()
        edge_support: Dict[str, float] = {}
        bonus_map = self.cfg.bonus_map or {
            "decision": self.cfg.bonus_decision,
            "outcome": self.cfg.bonus_outcome,
            "assumption": self.cfg.bonus_assumption,
        }
        for er in rows_edges:
            sid = str(er["id"])
            src_t = str(er["src_type"]) if er["src_type"] else ""
            dst_t = str(er["dst_type"]) if er["dst_type"] else ""
            strength = float(er["strength"]) if er["strength"] is not None else 0.0
            mult = max(bonus_map.get(src_t, 1.0), bonus_map.get(dst_t, 1.0))
            edge_support[sid] = edge_support.get(sid, 0.0) + strength * mult

        feats: Dict[str, Dict[str, float]] = {}
        for r in rows:
            sid = str(r["id"])
            feats[sid] = {
                "vec_sim": float(r["vec_sim"]),
                "lex": lex_map.get(sid, 0.0),
                "edge_support": edge_support.get(sid, 0.0),
                "created_at_epoch": float(r["created_at"].timestamp()),
            }
        return feats

    def _policy_filter(
        self,
        cur,
        org_id: str,
        user_id: str,
        acl_groups: Sequence[str],
        span_ids: List[str],
        now: datetime,
    ) -> List[str]:
        if not span_ids:
            return []

        # ACL: principal allowed via direct or via role
        cur.execute(
            """
            WITH allowed_spans AS (
              SELECT es.evidence_span_id::text AS id
              FROM evidence_span es
              JOIN artifact a ON a.artifact_id = es.artifact_id
              JOIN acl ON acl.acl_id = a.acl_id AND acl.org_id = es.org_id
              LEFT JOIN acl_allow aa_p ON aa_p.org_id = es.org_id AND aa_p.acl_id = a.acl_id
                                       AND aa_p.allow_type = 'principal' AND aa_p.principal_id = %s::uuid
              LEFT JOIN principal_role pr ON pr.org_id = es.org_id AND pr.principal_id = %s::uuid
              LEFT JOIN acl_allow aa_r ON aa_r.org_id = es.org_id AND aa_r.acl_id = a.acl_id
                                       AND aa_r.allow_type = 'role' AND aa_r.role_id = pr.role_id
              WHERE es.org_id = %s AND es.evidence_span_id = ANY(%s)
                AND (aa_p.acl_id IS NOT NULL OR aa_r.acl_id IS NOT NULL)
            )
            SELECT id FROM allowed_spans;
            """,
            (user_id, user_id, org_id, span_ids),
        )
        return [str(r["id"]) for r in cur.fetchall()]

    def _score_and_rank(self, feats: Dict[str, Dict[str, float]], allowed_ids: List[str]) -> List[Tuple[str, float]]:
        allowed_set = set(allowed_ids)

        vec = {sid: feats[sid]["vec_sim"] for sid in feats if sid in allowed_set}
        graph = {sid: feats[sid]["edge_support"] for sid in feats if sid in allowed_set}

        vec_n = _safe_normalize(vec)
        graph_n = _safe_normalize(graph)

        ranked: List[Tuple[str, float]] = []
        for sid in allowed_ids:
            f = feats.get(sid)
            if not f:
                continue
            created_at = datetime.fromtimestamp(f["created_at_epoch"], tz=timezone.utc)
            rec = _recency_bonus(created_at, self.cfg.recency_halflife_days)

            score = (
                self.cfg.alpha_vec * vec_n.get(sid, 0.0)
                + self.cfg.beta_bm25 * _safe_normalize({sid: feats[sid]["lex"] for sid in allowed_ids}).get(sid, 0.0)
                + self.cfg.gamma_graph * graph_n.get(sid, 0.0)
                + self.cfg.delta_recency * rec
            )
            ranked.append((sid, float(score)))

        ranked.sort(key=lambda t: t[1], reverse=True)
        return ranked

    def _cosine(self, a: Sequence[float], b: Sequence[float]) -> float:
        if not a or not b:
            return 0.0
        num = 0.0
        da = 0.0
        db = 0.0
        for x, y in zip(a, b):
            num += x * y
            da += x * x
            db += y * y
        if da <= 1e-12 or db <= 1e-12:
            return 0.0
        return num / (da ** 0.5 * db ** 0.5)

    def _span_embeddings(self, cur, span_ids: List[str]) -> Dict[str, List[float]]:
        if not span_ids:
            return {}
        cur.execute(
            """
            SELECT evidence_span_id::text as id, embedding
            FROM evidence_embedding
            WHERE evidence_span_id = ANY(%s)
            """,
            (span_ids,),
        )
        rows = cur.fetchall()
        # psycopg may return memoryview for vector; coerce to list of floats if needed
        def _to_floats(seq):
            try:
                return [float(x) for x in seq]
            except Exception:
                return []
        def _to_list(v):
            if isinstance(v, (bytes, bytearray, memoryview)):
                return _to_floats(list(v))
            return _to_floats(v)
        return {str(r["id"]): _to_list(r["embedding"]) for r in rows}

    def _mmr_select(
        self,
        query_embedding: Sequence[float],
        ranked: List[Tuple[str, float]],
        embed_map: Dict[str, Sequence[float]],
        k: int,
        lam: float,
    ) -> List[str]:
        candidates = [sid for sid, _ in ranked]
        selected: List[str] = []
        selected_set = set()
        # Pre-normalize scores (second element of ranked)
        score_map = {sid: s for sid, s in ranked}
        while candidates and len(selected) < k:
            best_sid = None
            best_value = -1e9
            for sid in candidates[:]:
                rel = score_map.get(sid, 0.0)
                div = 0.0
                if selected:
                    sim_to_sel = 0.0
                    for s2 in selected:
                        v1 = embed_map.get(sid)
                        v2 = embed_map.get(s2)
                        if v1 is None or v2 is None:
                            continue
                        sim_to_sel = max(sim_to_sel, self._cosine(v1, v2))
                    div = sim_to_sel
                value = lam * rel - (1.0 - lam) * div
                if value > best_value:
                    best_value = value
                    best_sid = sid
            if best_sid is None:
                break
            selected.append(best_sid)
            selected_set.add(best_sid)
            candidates = [c for c in candidates if c != best_sid]
        return selected

    def _dedup_by_artifact_overlap(self, spans: List[Dict[str, Any]], max_k: int) -> List[Dict[str, Any]]:
        """Remove overlapping spans per artifact, keep first occurrences in order."""
        out: List[Dict[str, Any]] = []
        seen = {}
        for s in spans:
            if len(out) >= max_k:
                break
            aid = s.get("artifact_id")
            st = int(s.get("start_char", 0) or 0)
            en = int(s.get("end_char", 0) or 0)
            if st > en:
                st, en = en, st
            overlaps = False
            lst = seen.setdefault(aid, [])
            for (a,b) in lst:
                if max(st, a) < min(en, b):
                    overlaps = True
                    break
            if overlaps:
                continue
            lst.append((st,en))
            out.append(s)
        return out

    def _hydrate_spans(self, cur, org_id: str, span_ids: List[str]) -> List[Dict[str, Any]]:
        if not span_ids:
            return []
        cur.execute(
            """
            SELECT 
                es.evidence_span_id::text as id, 
                es.artifact_id::text, 
                es.start_char, 
                es.end_char, 
                SUBSTRING(at.text_utf8 FROM es.start_char+1 FOR es.end_char-es.start_char) as text,
                es.created_at,
                es.confidence
            FROM evidence_span es
            JOIN artifact_text at ON es.artifact_text_id = at.artifact_text_id
            WHERE es.org_id = %s
              AND es.evidence_span_id = ANY(%s)
            """,
            (org_id, span_ids),
        )
        rows = cur.fetchall()
        by_id = {str(r["id"]): dict(r) for r in rows}
        ordered = [by_id[sid] for sid in span_ids if sid in by_id]
        return self._dedup_by_artifact_overlap(ordered, max_k=len(span_ids))
