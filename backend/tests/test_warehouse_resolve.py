from app.analytics.warehouse import resolve_db


def test_prefers_local_build_then_snapshot(tmp_path):
    cache, snap = tmp_path / "cache", tmp_path / "data" / "analytics.duckdb"
    cache.mkdir()
    assert resolve_db(cache, snap) is None
    snap.parent.mkdir()
    snap.write_bytes(b"x")
    assert resolve_db(cache, snap) == snap
    (cache / "analytics.duckdb").write_bytes(b"y")
    assert resolve_db(cache, snap) == cache / "analytics.duckdb"