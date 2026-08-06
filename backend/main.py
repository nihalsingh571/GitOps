"""
Backend API — FastAPI
Endpoints:
  GET  /health   → liveness probe target
  GET  /ready    → readiness probe target (checks DB)
  GET  /items    → list all items from Postgres
  POST /items    → create a new item
  GET  /metrics  → Prometheus metrics (auto-exposed by instrumentator)
"""

import os
import time
import logging
from contextlib import asynccontextmanager

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── DB config from environment (injected via Kubernetes Secret/ConfigMap) ─────
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASS = os.getenv("DB_PASS", "changeme")

_db_ready = False  # flipped to True once init_db succeeds (used only for table creation)


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS, connect_timeout=3
    )


def init_db():
    """Create the items table if it doesn't exist."""
    global _db_ready
    for attempt in range(5):  # 5 attempts * 3s = 15s max at startup
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id   SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
            conn.commit()
            conn.close()
            _db_ready = True
            log.info("Database initialised successfully.")
            return
        except Exception as exc:
            log.warning("DB not ready (attempt %d/10): %s", attempt + 1, exc)
            time.sleep(3)
    log.error("Could not connect to database after 10 attempts.")


# ── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield  # app runs here
    log.info("Shutting down.")


app = FastAPI(title="GitOps Demo API", version="1.0.0", lifespan=lifespan)

# Expose /metrics endpoint automatically
Instrumentator().instrument(app).expose(app)

# Allow the frontend (served on a different origin in local dev) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────
class ItemIn(BaseModel):
    name: str


class ItemOut(BaseModel):
    id: int
    name: str


# ── Probes ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["probes"])
def liveness():
    """
    Liveness probe — Kubernetes calls this periodically.
    If it returns non-2xx, the container is restarted.
    We keep it ultra-cheap: just confirm the process is alive.
    """
    return {"status": "alive"}


@app.get("/ready", tags=["probes"])
def readiness():
    """
    Readiness probe — Kubernetes calls this before sending traffic.
    If it returns non-2xx, the pod is removed from Service endpoints
    (traffic stops, but the container is NOT restarted).
    We ALWAYS attempt a live DB connection here — never rely on a startup
    flag, because Postgres may have been unavailable at boot but is now up.
    This pattern correctly handles slow DB startups and restarts.
    """
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ready", "db": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DB unreachable: {exc}")


# ── Business logic ────────────────────────────────────────────────────────────
@app.get("/items", response_model=list[ItemOut], tags=["items"])
def list_items():
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM items ORDER BY id DESC LIMIT 100")
            rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1]} for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/items", response_model=ItemOut, status_code=201, tags=["items"])
def create_item(item: ItemIn):
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO items (name) VALUES (%s) RETURNING id, name",
                (item.name,)
            )
            row = cur.fetchone()
        conn.commit()
        conn.close()
        return {"id": row[0], "name": row[1]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
