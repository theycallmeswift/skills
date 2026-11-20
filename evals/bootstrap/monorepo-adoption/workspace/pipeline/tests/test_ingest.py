from pathlib import Path

from pipeline.ingest import active, build_digest, load_sources

DATA = Path(__file__).resolve().parents[1] / "data"


def test_active_skips_disabled():
    sources = [{"name": "a"}, {"name": "b", "enabled": False}]
    assert active(sources) == [{"name": "a"}]


def test_build_digest_caps_items():
    items = [{"title": f"t{i}", "source": "s"} for i in range(20)]
    assert len(build_digest(items, limit=3).splitlines()) == 3


def test_real_sources_load():
    sources = load_sources(DATA)
    assert any(s["name"] == "hn" for s in sources)
