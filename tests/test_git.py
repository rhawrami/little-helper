import json

import polars as pl
import pytest

from little_helper import config, paths, store
from little_helper.collect import git as gitc
from little_helper.normalize import git as gitn
from little_helper.normalize import read_table


@pytest.fixture
def project(tiny_repo, monkeypatch):
    s = dict(config.study()["git"])
    s["reserve_free_gb"] = 0
    monkeypatch.setattr(gitc, "settings", lambda: s)
    repo = config.Repo(key="example.org/demo/tiny", clone_urls=["/nonexistent/first-url-fails", str(tiny_repo)],
                       size_mb=1)
    return config.Project(id="demo", name="Demo", regime="A", repos=[repo], collect={"git": True})


def test_collect_extracts_everything_and_deletes_clone(lh_env, project):
    rows = gitc.run([project], jobs=2, log=lambda m: None)
    assert [r["status"] for r in rows] == ["ok"], rows
    runs = gitc.successful_runs("example.org/demo/tiny")
    assert len(runs) == 1
    meta = json.loads((runs[0] / "meta.json").read_text())
    assert meta["commits"] == 6 and meta["extractor_version"] == gitc.EXTRACTOR_VERSION
    assert meta["clone_url"].endswith("src-repo")  # fell back past the failing URL
    assert not (paths.work_dir() / "git" / "example.org").exists()  # clone and empty parents removed

    commits = pl.read_parquet(runs[0] / "commits-*.parquet")
    by_subject = {m.split("\n")[0]: r for m, r in zip(commits["message"], commits.iter_rows(named=True))}
    assert by_subject["Drop old test"]["on_default"] and not by_subject["Drop old test"]["first_parent"]
    assert by_subject["Fix overflow in a"]["author_date"] == "2021-03-01T09:30:00-05:00"
    assert len(by_subject["Merge branch 'feature'"]["parents"]) == 2

    files = pl.read_parquet(runs[0] / "files-*.parquet")
    init = files.filter(pl.col("sha") == by_subject["Initial import"]["sha"])
    assert set(init["change"]) == {"A"}
    png = init.filter(pl.col("path") == "logo.png").row(0, named=True)
    assert png["added"] is None and png["deleted"] is None  # binary
    assert {"weird\tname.txt", "dócs/ñ.md"} <= set(files["path"])  # quoted and non-ASCII paths decoded
    fix = files.filter((pl.col("sha") == by_subject["Fix overflow in a"]["sha"]) & (pl.col("path") == "src/a.c"))
    assert fix.select("added", "deleted", "change").row(0) == (2, 1, "M")
    drop = files.filter(pl.col("sha") == by_subject["Drop old test"]["sha"]).row(0, named=True)
    assert drop["change"] == "D" and drop["path"] == "tests/test_a.py"
    assert files.filter(pl.col("sha") == by_subject["Merge branch 'feature'"]["sha"]).height == 0

    refs = pl.read_parquet(runs[0] / "refs.parquet")
    v10 = refs.filter(pl.col("ref") == "refs/tags/v1.0").row(0, named=True)
    assert v10["object_type"] == "tag" and v10["peeled"] == by_subject["Fix overflow in a"]["sha"]

    trees = pl.read_parquet(runs[0] / "trees.parquet")
    assert {"2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01", "head"} <= set(trees["snapshot"])
    assert trees.filter(pl.col("snapshot") == "2020-01-01")["path"].to_list().count("CONTRIBUTING.md") == 1

    pol = pl.read_parquet(runs[0] / "policy_files.parquet")
    assert set(pol["path"]) == {"CONTRIBUTING.md", "AGENTS.md"}
    assert pol.filter(pl.col("path") == "CONTRIBUTING.md").height == 2  # two versions
    assert any("must be disclosed" in c for c in pol["content"])

    entries = [json.loads(line) for f in paths.manifest_dir().glob("git/*.jsonl") for line in f.read_text().splitlines()]
    assert {e["file"].split("/")[-1] for e in entries} >= {"meta.json", "refs.parquet", "commits-00000.parquet"}
    for e in entries:
        assert store.sha256_file(paths.resolve_data_file(e["file"])) == e["sha256"]

    again = gitc.run([project], log=lambda m: None)
    assert again[0]["status"].startswith("skipped")


def test_normalize_git_tables(lh_env, project):
    gitc.run([project], log=lambda m: None)
    res = gitn.normalize_project(project)
    assert res["commits"] == 6
    c = read_table("commits", "demo")
    fix = c.filter(pl.col("subject") == "Fix overflow in a").row(0, named=True)
    assert str(fix["author_time"]) == "2021-03-01 14:30:00+00:00" and fix["author_tz"] == -300
    assert c.filter(pl.col("subject") == "Drop old test")["author_is_bot"].item()
    t = read_table("trailers", "demo")
    assert set(t["key"]) == {"signed-off-by", "assisted-by", "co-authored-by"}
    m = read_table("ai_markers", "demo")
    assert {"trailer_assisted_by", "trailer_coauthor_ai"} <= set(m["marker"])
    f = read_table("commit_files", "demo")
    flags = {r["path"]: r for r in f.iter_rows(named=True)}
    assert flags["tests/test_a.py"]["is_test"] and flags["CONTRIBUTING.md"]["is_docs"]
    assert flags["src/a.c"]["top_dir"] == "src" and flags["src/a.c"]["ext"] == "c"
    refs = read_table("refs", "demo")
    assert set(refs.filter(pl.col("kind") == "tag")["name"]) == {"v0.9", "v1.0"}
    pol = read_table("policy_files", "demo")
    assert pol["committer_time"].null_count() == 0


def test_snapshot_dates():
    from datetime import datetime, timezone
    now = datetime(2024, 5, 1, tzinfo=timezone.utc)
    assert gitc.snapshot_dates("2022-06-30T00:00:00+00:00", "yearly", now) == ["2023-01-01T00:00:00Z", "2024-01-01T00:00:00Z"]
    assert gitc.snapshot_dates("2023-11-30T00:00:00+00:00", "quarterly", now) == ["2024-01-01T00:00:00Z", "2024-04-01T00:00:00Z"]
    assert gitc.snapshot_dates(None, "yearly") == []


def test_policy_regex_matches_expected_paths():
    rx = gitc.policy_regex(["Documentation/process/coding-assistants.rst"])
    hits = ["AGENTS.md", "pkg/sub/AGENTS.md", ".github/copilot-instructions.md", "CONTRIBUTING.rst",
            ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md", ".cursor/rules/style.mdc", "doc/ai-policy.md",
            "Documentation/process/coding-assistants.rst", "CLAUDE.md"]
    misses = ["src/contributing.c", "third_party/x/CONTRIBUTING.md", "README.md", "src/agents.py"]
    assert all(rx.search(p) for p in hits), [p for p in hits if not rx.search(p)]
    assert not any(rx.search(p) for p in misses), [p for p in misses if rx.search(p)]
