from datetime import date

from app.api.worker import run


class Store:
    def __init__(self, jobs=1):
        self.jobs = [{"id": f"j{i}", "cik": "0000719739", "as_of": date(2023, 3, 10), "decision": "d"} for i in range(jobs)]
        self.rows = {j["id"]: {"status": "queued"} for j in self.jobs}
        self.beats, self.offline = [], []

    def claim_next(self):
        return self.jobs.pop(0) if self.jobs else None

    def heartbeat(self, worker_id, job, rerank):
        self.beats.append((worker_id, job))

    def worker_offline(self, worker_id):
        self.offline.append(worker_id)

    def update(self, job_id, **fields):
        self.rows[job_id].update(fields)

    def get(self, job_id):
        return self.rows[job_id]


def runner(cik, as_of, decision, on_event):
    on_event([{"node": "redact", "message": "ok", "ms": 1}])
    return {"allowed": True, "report": {"cik": cik}}


def test_worker_runs_one_job_and_goes_offline():
    s, logs = Store(), []
    assert run(store=s, runner=runner, once=True, warm=False, log=logs.append) == 1
    assert s.rows["j0"]["status"] == "done" and s.rows["j0"]["report"]["retrieval_mode"]
    assert any(job == "j0" for _, job in s.beats) and s.offline
    assert any("-> done" in line for line in logs)


def test_worker_once_with_empty_queue():
    s = Store(jobs=0)
    assert run(store=s, runner=runner, once=True, warm=False, log=lambda m: None) == 0 and s.offline