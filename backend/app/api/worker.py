"""Analysis worker: runs queued Crash-Tests with the full pipeline (both local ONNX models, rerank top-20).

The Render free instance (512 MB) only queues jobs (RUN_JOBS_INLINE=false). Run this on a machine with enough
memory. It needs only outbound internet (Supabase, Neo4j, LLM APIs): no open port, no tunnel.

    python -m app.api.worker            # keep running, Ctrl+C to stop
    python -m app.api.worker --once     # run at most one queued job, then exit
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
import uuid
from typing import Any, Callable

from app.api.routes import execute, get_store, graph_runner
from app.config import get_settings
from app.db import DatabaseError

HEARTBEAT_SECONDS = 30
POLL_SECONDS = 3
DB_RETRY_SECONDS = 10


def _beat(store: Any, worker_id: str, state: dict, rerank: bool, stop: threading.Event, log: Callable) -> None:
    while not stop.is_set():
        try:
            store.heartbeat(worker_id, state.get("job"), rerank)
        except DatabaseError as exc:
            log(f"heartbeat failed: {exc}")
        stop.wait(HEARTBEAT_SECONDS)


def warm_up() -> None:
    """Load the embedder and reranker once so the first job does not pay the model load time."""
    from app.rag.retrieve import retrieve
    retrieve("board risk oversight", k=1, cik="0000719739")


def run(store: Any = None, runner: Callable | None = None, once: bool = False, warm: bool = True,
        log: Callable[[str], None] = lambda m: print(m, flush=True)) -> int:
    """Returns the number of jobs processed."""
    store = store or get_store()
    runner = runner or graph_runner
    rerank = get_settings().rerank_enabled
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    state: dict = {"job": None}
    stop = threading.Event()
    threading.Thread(target=_beat, args=(store, worker_id, state, rerank, stop, log), daemon=True).start()
    log(f"{worker_id} online (rerank {'on' if rerank else 'off'})")
    if warm:
        started = time.perf_counter()
        try:
            warm_up()
            log(f"models warm in {time.perf_counter() - started:.0f} s")
        except Exception as exc:  # warm-up is an optimisation; jobs still run without it
            log(f"warm-up skipped: {type(exc).__name__}: {exc}")
    log("waiting for queued Crash-Tests (Ctrl+C to stop)")
    done = 0
    try:
        while True:
            try:
                job = store.claim_next()
            except DatabaseError as exc:
                log(f"database unavailable, retrying in {DB_RETRY_SECONDS} s: {exc}")
                time.sleep(DB_RETRY_SECONDS)
                continue
            if job is None:
                if once:
                    break
                time.sleep(POLL_SECONDS)
                continue
            state["job"] = job["id"]
            try:
                store.heartbeat(worker_id, job["id"], rerank)
            except DatabaseError:
                pass
            log(f"running {job['id']} cik={job['cik']} as_of={job['as_of']}")
            started = time.perf_counter()
            execute(job["id"], job["cik"], job["as_of"], job["decision"], store, runner)
            row = store.get(job["id"]) or {}
            log(f"  -> {row.get('status')} in {time.perf_counter() - started:.0f} s {row.get('error') or ''}".rstrip())
            state["job"] = None
            done += 1
            if once:
                break
    except KeyboardInterrupt:
        log("stopping")
    finally:
        stop.set()
        try:
            store.worker_offline(worker_id)
        except DatabaseError:
            pass
    return done


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Nirikkha analysis worker")
    parser.add_argument("--once", action="store_true", help="run at most one queued job, then exit")
    parser.add_argument("--no-warm", action="store_true", help="skip loading the models at start")
    args = parser.parse_args(argv[1:])
    run(once=args.once, warm=not args.no_warm)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))