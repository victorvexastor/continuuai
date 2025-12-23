"""ContinuuAI Pattern Analyzer Service - Proactive insight generation."""
from __future__ import annotations

import logging
import os
import json
from contextlib import contextmanager
from typing import List, Dict, Any

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from detectors import (
    RevisitDueDetector,
    UnresolvedDissentDetector,
    AssumptionDriftDetector,
    DecisionConflictDetector,
    ValuesConflictDetector,
    OutcomeNeededDetector,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("pattern-analyzer")

app = FastAPI(title="ContinuuAI Pattern Analyzer", version="0.1.0")

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
ANALYSIS_SCHEDULE = os.environ.get("ANALYSIS_SCHEDULE", "0 */6 * * *")  # Every 6 hours
RUN_ON_STARTUP = os.environ.get("RUN_ON_STARTUP", "false").lower() == "true"

# Scheduler
scheduler = BackgroundScheduler()


class AnalyzeRequest(BaseModel):
    """Request to analyze a specific org."""

    org_id: str | None = None  # If None, analyze all orgs


class AnalyzeResponse(BaseModel):
    """Response from analysis."""

    orgs_analyzed: List[str]
    insights_generated: int
    insights_by_type: Dict[str, int]
    errors: List[str]


@contextmanager
def get_db_connection():
    """Get database connection."""
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


@app.get("/healthz")
def healthz():
    """Health check."""
    return {"ok": True, "service": "pattern-analyzer", "schedule": ANALYSIS_SCHEDULE}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Run pattern analysis for one or all orgs.

    If org_id is provided, analyze only that org.
    If org_id is None, analyze all orgs.
    """
    logger.info(f"Analysis requested for org_id={req.org_id}")

    try:
        with get_db_connection() as conn:
            if req.org_id:
                orgs_to_analyze = [req.org_id]
            else:
                orgs_to_analyze = _get_all_orgs(conn)

            total_insights = 0
            insights_by_type: Dict[str, int] = {}
            errors = []

            for org_id in orgs_to_analyze:
                try:
                    insights = analyze_org(conn, org_id)
                    total_insights += len(insights)

                    # Count by type
                    for insight in insights:
                        insight_type = insight["insight_type"]
                        insights_by_type[insight_type] = insights_by_type.get(insight_type, 0) + 1

                except Exception as e:
                    logger.error(f"Error analyzing org {org_id}: {e}", exc_info=True)
                    errors.append(f"org {org_id}: {str(e)}")

            return AnalyzeResponse(
                orgs_analyzed=orgs_to_analyze,
                insights_generated=total_insights,
                insights_by_type=insights_by_type,
                errors=errors,
            )

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def analyze_org(conn: psycopg.Connection, org_id: str) -> List[Dict[str, Any]]:
    """
    Run all detectors for a single org.

    Returns list of generated insights.
    """
    logger.info(f"Analyzing org {org_id}")

    # Clear old insights (keep for 30 days, then archive)
    _archive_old_insights(conn, org_id)

    all_insights = []

    # Initialize all detectors
    detectors = [
        RevisitDueDetector(conn, org_id),
        UnresolvedDissentDetector(conn, org_id),
        AssumptionDriftDetector(conn, org_id),
        DecisionConflictDetector(conn, org_id),
        ValuesConflictDetector(conn, org_id),
        OutcomeNeededDetector(conn, org_id),
    ]

    # Run each detector
    for detector in detectors:
        try:
            insights = detector.detect()
            all_insights.extend(insights)
            logger.info(
                f"[{detector.__class__.__name__}] Generated {len(insights)} insights for org {org_id}"
            )
        except Exception as e:
            logger.error(
                f"[{detector.__class__.__name__}] Failed for org {org_id}: {e}",
                exc_info=True,
            )

    # Store insights in database
    _store_insights(conn, all_insights)

    logger.info(f"Completed analysis for org {org_id}: {len(all_insights)} total insights")

    return all_insights


def _get_all_orgs(conn: psycopg.Connection) -> List[str]:
    """Get all organization IDs."""
    query = "SELECT org_id FROM org"
    with conn.cursor() as cur:
        cur.execute(query)
        return [str(row[0]) for row in cur.fetchall()]


def _archive_old_insights(conn: psycopg.Connection, org_id: str):
    """Mark insights older than 30 days as resolved."""
    query = """
        UPDATE insight
        SET status = 'resolved'
        WHERE org_id = %s
          AND status = 'active'
          AND created_at < NOW() - INTERVAL '30 days'
    """
    with conn.cursor() as cur:
        cur.execute(query, (org_id,))
    conn.commit()


def _store_insights(conn: psycopg.Connection, insights: List[Dict[str, Any]]):
    """Store insights in database."""
    if not insights:
        return

    insert_query = """
        INSERT INTO insight (
            org_id,
            insight_type,
            severity,
            title,
            description,
            decision_ids,
            evidence,
            status
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (org_id, insight_type, title, status)
        DO UPDATE SET
            description = EXCLUDED.description,
            decision_ids = EXCLUDED.decision_ids,
            evidence = EXCLUDED.evidence,
            updated_at = NOW()
    """

    with conn.cursor() as cur:
        for insight in insights:
            cur.execute(
                insert_query,
                (
                    insight["org_id"],
                    insight["insight_type"],
                    insight["severity"],
                    insight["title"],
                    insight["description"],
                    insight["decision_ids"],
                    json.dumps(insight["evidence"]),
                    insight["status"],
                ),
            )

    conn.commit()
    logger.info(f"Stored {len(insights)} insights in database")


def scheduled_analysis():
    """Run analysis for all orgs on schedule."""
    logger.info("Running scheduled analysis for all orgs")

    try:
        with get_db_connection() as conn:
            orgs = _get_all_orgs(conn)

            for org_id in orgs:
                try:
                    analyze_org(conn, org_id)
                except Exception as e:
                    logger.error(f"Scheduled analysis failed for org {org_id}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Scheduled analysis failed: {e}", exc_info=True)


@app.on_event("startup")
def startup():
    """Start scheduler on app startup."""
    logger.info(f"Starting pattern analyzer with schedule: {ANALYSIS_SCHEDULE}")

    # Add scheduled job
    scheduler.add_job(
        scheduled_analysis,
        trigger=CronTrigger.from_crontab(ANALYSIS_SCHEDULE),
        id="pattern_analysis",
        name="Pattern Analysis for All Orgs",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")

    # Optionally run analysis on startup
    if RUN_ON_STARTUP:
        logger.info("Running initial analysis on startup")
        try:
            scheduled_analysis()
        except Exception as e:
            logger.error(f"Startup analysis failed: {e}", exc_info=True)


@app.on_event("shutdown")
def shutdown():
    """Shutdown scheduler."""
    logger.info("Shutting down pattern analyzer")
    scheduler.shutdown()
