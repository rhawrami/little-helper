"""Object storage (DigitalOcean Spaces in production) against moto's in-memory S3."""

import os
import time

import boto3
import polars as pl
import pytest
from moto import mock_aws

from little_helper import config, objects, paths, store
from little_helper.collect import git as gitc
from little_helper.collect import github as ghc
from little_helper.normalize import git as gitn
from little_helper.normalize import github as ghn
from little_helper.normalize import partition_path, read_table

from test_github import FakeGitHub, crawl, pr

BUCKET = "lh-test"


@pytest.fixture
def s3(lh_env, monkeypatch, tmp_path):
    for k, v in {"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
                 "AWS_DEFAULT_REGION": "us-east-1", "AWS_SHARED_CREDENTIALS_FILE": str(tmp_path / "none"),
                 "AWS_CONFIG_FILE": str(tmp_path / "none"), "LH_S3_BUCKET": BUCKET, "LH_S3_PREFIX": "study"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    objects._client_for.cache_clear()
    objects._pending.clear()
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client
    objects._client_for.cache_clear()


def keys(client) -> set[str]:
    return {o["Key"] for o in client.list_objects_v2(Bucket=BUCKET).get("Contents", [])}


def test_spaces_endpoint_sets_the_region(lh_env, monkeypatch):
    assert objects.settings() is None and objects.describe().startswith("off")
    monkeypatch.setenv("LH_S3_BUCKET", "b")
    monkeypatch.setenv("LH_S3_ENDPOINT", "https://nyc3.digitaloceanspaces.com")
    s = objects.settings()
    assert s.region == "nyc3" and s.prefix == "little-helper" and not s.keep_local and objects.pruning()


def test_github_raw_goes_to_the_bucket_and_is_read_back(s3, monkeypatch):
    sets = dict(ghc.settings(), pr_page_size=2, chunk_pages=1)
    monkeypatch.setattr(ghc, "settings", lambda: sets)
    repo = config.Repo(key="github.com/o/r", clone_urls=[], github="o/r")
    project = config.Project(id="demo", name="Demo", regime="A", repos=[repo], collect={"github_prs": True})
    out = crawl(project, repo, FakeGitHub([pr(i) for i in range(1, 6)]), "20260101T000000Z")
    assert out["items"] == 5

    run = paths.raw_dir("github", "github.com/o/r", "20260101T000000Z")
    assert not list(run.glob("*.jsonl.zst"))  # verified in the bucket, then deleted locally
    assert (run / "queries.json").exists()
    k = keys(s3)
    base = "study/raw/github/github.com/o/r/20260101T000000Z/"
    assert {base + f"prs-0000{i}.jsonl.zst" for i in (1, 2, 3)} <= k  # chunk numbering survives pruning
    assert "study/state/github/github.com/o/r.json" in k
    assert any(x.startswith("study/manifests/github/") for x in k)
    head = s3.head_object(Bucket=BUCKET, Key=base + "prs-00001.jsonl.zst")
    manifest = next(paths.manifest_dir().glob("github/*.jsonl")).read_text()
    assert head["Metadata"]["sha256"] in manifest

    t = ghn.normalize_repo(project, repo)
    assert t["change_proposals"].height == 5
    assert not list(run.glob("*.jsonl.zst"))  # downloaded one at a time and removed again


def test_git_extract_and_canonical_tables_live_in_the_bucket(s3, tiny_repo, monkeypatch):
    sets = dict(config.study()["git"], reserve_free_gb=0)
    monkeypatch.setattr(gitc, "settings", lambda: sets)
    repo = config.Repo(key="example.org/demo/tiny", clone_urls=[str(tiny_repo)], size_mb=1)
    project = config.Project(id="demo", name="Demo", regime="A", repos=[repo], collect={"git": True})
    assert gitc.run([project], log=lambda m: None)[0]["status"] == "ok"
    run = gitc.successful_runs(repo.key)[0]
    assert [p.name for p in run.iterdir()] == ["meta.json"]  # the record of the run stays local
    assert gitc.run([project], log=lambda m: None)[0]["status"].startswith("skipped")

    assert gitn.normalize_project(project)["commits"] == 6
    assert not partition_path("commits", "demo").exists()
    assert "study/canonical/commits/project=demo/part-0.parquet" in keys(s3)
    assert read_table("commits", "demo").height == 6
    assert read_table("commits").height == 6
    assert not partition_path("commits", "demo").exists()


def test_raw_objects_are_never_overwritten(s3):
    raw = paths.raw_dir("x", "a.json")
    store.atomic_write_bytes(raw, b"one")
    assert objects.upload(raw) == "uploaded" and objects.upload(raw) == "present"
    store.atomic_write_bytes(raw, b"two")
    with pytest.raises(objects.Conflict):
        objects.upload(raw)
    state = paths.state_dir("x.json")
    store.atomic_write_bytes(state, b"one")
    objects.upload(state)
    store.atomic_write_bytes(state, b"two")
    assert objects.upload(state) == "uploaded"  # bookkeeping is mutable


def test_failed_upload_stays_local_and_is_retried(s3, monkeypatch):
    chunk = paths.raw_dir("github", "k", "run", "prs-00001.jsonl.zst")
    store.atomic_write_bytes(chunk, b"pages")
    monkeypatch.setenv("LH_S3_BUCKET", "no-such-bucket")
    assert objects.settle(chunk) is False and chunk.exists()
    monkeypatch.setenv("LH_S3_BUCKET", BUCKET)
    assert objects.retry_pending(log=lambda m: None) == 0 and not chunk.exists()

    # A crash loses the in-memory retry list; the next run's catch-up finds the file.
    left = paths.raw_dir("github", "k", "run", "prs-00002.jsonl.zst")
    store.atomic_write_bytes(left, b"more pages")
    assert objects.catch_up(log=lambda m: None) == 0  # too recent: another lh may be writing it
    old = time.time() - 2 * objects.CATCH_UP_AGE
    os.utime(left, (old, old))
    assert objects.catch_up(log=lambda m: None) == 1 and not left.exists()
    assert "study/raw/github/k/run/prs-00002.jsonl.zst" in keys(s3)


def test_push_from_one_machine_then_pull_on_another(s3, monkeypatch, tmp_path):
    monkeypatch.delenv("LH_S3_BUCKET")  # machine A collected without object storage
    run = paths.raw_dir("github", "github.com/o/r", "run1")
    store.atomic_write_bytes(run / "prs-00001.jsonl.zst", b"pages")
    store.atomic_write_bytes(run / "queries.json", b"{}")
    store.atomic_write_bytes(paths.raw_dir("git", "example.org/a/b", "run1", "meta.json"), b'{"status": "ok"}')
    store.atomic_write_bytes(paths.state_dir("github", "github.com/o/r.json"), b'{"prs": {}}')
    pl.DataFrame({"repo": ["o/r"]}).write_parquet(paths.derived_dir("selection").mkdir(parents=True) or
                                                  paths.derived_dir("selection", "github_probe.parquet"))
    store.atomic_write_bytes(paths.manifest_dir() / "github" / "run1.jsonl", b"{}\n")

    monkeypatch.setenv("LH_S3_BUCKET", BUCKET)
    c = objects.push(log=lambda m: None)
    assert (c["uploaded"], c["failed"], c["conflicts"]) == (6, 0, 0)
    assert objects.push(log=lambda m: None)["present"] == 6  # idempotent
    assert run.joinpath("prs-00001.jsonl.zst").exists()  # push keeps local copies unless --prune

    # Machine B starts empty and must sync before collecting.
    monkeypatch.setenv("LH_DATA_DIR", str(tmp_path / "b-data"))
    monkeypatch.setenv("LH_MANIFEST_DIR", str(tmp_path / "b-manifests"))
    with pytest.raises(SystemExit, match="sync pull"):
        objects.preflight()
    c = objects.pull(log=lambda m: None)
    assert c["downloaded"] == 3  # state, git meta.json, derived; not chunks, queries or manifests
    objects.preflight()
    b_run = paths.raw_dir("github", "github.com/o/r", "run1")
    assert store.load_state(paths.state_dir("github", "github.com/o/r.json")) == {"prs": {}}
    assert not (b_run / "prs-00001.jsonl.zst").exists()
    assert objects.list_files(b_run, "*.jsonl.zst") == [b_run / "prs-00001.jsonl.zst"]
    assert objects.subdirs(paths.raw_dir("github", "github.com/o/r")) == [b_run]
