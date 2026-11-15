import json

import polars as pl

from little_helper import paths, store
from little_helper.classify import ai_markers, bots, trailers
from little_helper.classify import paths as path_rules


def test_page_writer_commits_atomically(lh_env):
    m = store.Manifest("demo", "20260101T000000Z")
    d = paths.raw_dir("demo", "run1")
    w = store.PageWriter(d, "prs", m, repo="o/r")
    assert w.commit() is None  # nothing buffered, nothing written
    w.write({"a": 1})
    w.write({"b": "ü"})
    assert not list(d.glob("*.zst"))  # nothing visible before commit
    f = w.commit()
    assert f.name == "prs-00001.jsonl.zst" and not list(d.glob("*.tmp"))
    assert list(store.iter_records(f)) == [{"a": 1}, {"b": "ü"}]
    entry = json.loads(m.path.read_text().splitlines()[0])
    assert entry["records"] == 2 and entry["repo"] == "o/r" and entry["file"] == "raw/demo/run1/prs-00001.jsonl.zst"
    assert entry["sha256"] == store.sha256_file(f)
    w.write({"c": 3})
    assert w.commit().name == "prs-00002.jsonl.zst"


def test_legacy_manifest_paths_resolve(lh_env):
    assert paths.resolve_data_file("data/raw/debian/x/y") == paths.data_dir() / "raw/debian/x/y"
    assert paths.resolve_data_file("raw/github/a") == paths.data_dir() / "raw/github/a"


def test_trailers():
    assert trailers.parse("Fix it\n\nSigned-off-by: A <a@x>\nReviewed-by: B <b@x>") == [
        ("signed-off-by", "A <a@x>"), ("reviewed-by", "B <b@x>")]
    assert trailers.parse("Subject only: with a colon") == []
    assert trailers.parse("Fix\n\nThis is prose.\nNote: it continues for a while\nand more prose here.") == []
    assert trailers.parse("Fix\n\nLink: https://x\n  continued") == [("link", "https://x continued")]
    assert trailers.parse("Fix\n\nbody\n\nChange-Id: I123\nSigned-off-by: A") == [
        ("change-id", "I123"), ("signed-off-by", "A")]


def test_path_rules():
    df = pl.DataFrame({"path": ["tests/test_x.py", "pkg/foo_test.go", "src/app.test.ts", "src/main.c",
                                "third_party/zlib/inflate.c", "package-lock.json", "docs/index.rst",
                                ".github/workflows/ci.yml", "CMakeLists.txt", "lib/Foo.java", "lib/FooTest.java"]})
    out = {r["path"]: r for r in path_rules.add_flags(df).iter_rows(named=True)}
    assert out["tests/test_x.py"]["is_test"] and out["pkg/foo_test.go"]["is_test"] and out["src/app.test.ts"]["is_test"]
    assert out["lib/FooTest.java"]["is_test"] and not out["lib/Foo.java"]["is_test"]
    assert not out["src/main.c"]["is_test"] and out["src/main.c"]["top_dir"] == "src" and out["src/main.c"]["ext"] == "c"
    assert out["third_party/zlib/inflate.c"]["is_vendored"]
    assert out["package-lock.json"]["is_generated"] and out["docs/index.rst"]["is_docs"]
    assert out[".github/workflows/ci.yml"]["is_ci"] and out["CMakeLists.txt"]["is_build"]
    custom = path_rules.add_flags(df, overrides={"test": [r"^lib/Foo\.java$"]})
    assert custom.filter(pl.col("path") == "lib/Foo.java")["is_test"].item()


def test_ai_markers_and_bots():
    assert ai_markers.find("message", "Fix\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)")[0]["tool"] == "claude"
    hit = ai_markers.find("message", "x\n\nCo-authored-by: GitHub Copilot <copilot@github.com>")
    assert hit and hit[0]["marker"] == "trailer_coauthor_ai" and hit[0]["tool"] == "copilot"
    assert ai_markers.find("message", "x\n\nCo-authored-by: Jane Doe <jane@example.org>") == []
    # People, not tools (curl has used Assisted-by for human helpers since 2013).
    for human in ("Assisted-by: Jay Satiro", "Assisted-by: Claude Paroz <claude@example.org>",
                  "Co-authored-by: Claude Monet <cm@example.org>", "Generated-by: tools/gen.sh"):
        assert ai_markers.find("message", f"x\n\n{human}") == [], human
    for tool, text in (("claude", "Assisted-by: Opus 4.7"), ("claude", "Assisted-by: Claude:claude-opus-5 coccinelle"),
                       ("claude", "Co-Authored-By: Claude <noreply@anthropic.com>"), ("openai", "Assisted-by: GPT-5.6 Luna"),
                       ("gemini", "Assisted-by: Gemini 3 Pro")):
        hits = ai_markers.find("message", f"x\n\n{text}")
        assert hits and hits[0]["tool"] == tool, (text, hits)
    assert ai_markers.find("login", "copilot-swe-agent[bot]")[0]["marker"] == "bot_author"
    assert ai_markers.find("branch", "codex/fix-typo")[0]["marker"] == "branch_prefix"
    assert ai_markers.find("branch", "fix-codex-typo") == []
    assert bots.is_bot_login("dependabot[bot]") and bots.is_bot_login("anyone", "Bot") and not bots.is_bot_login("octocat")
    assert bots.is_bot_identity("github-actions", "41898282+github-actions[bot]@users.noreply.github.com")
    assert not bots.is_bot_identity("Ada Dev", "ada@example.org")
