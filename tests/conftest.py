import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def lh_env(tmp_path, monkeypatch):
    """Point every data location at a temporary directory, with object storage off and
    this machine's config/local.yaml ignored."""
    from little_helper import paths
    monkeypatch.setattr(paths, "_local", lambda: {})
    for name in ("LH_S3_BUCKET", "LH_S3_ENDPOINT", "LH_S3_PREFIX", "LH_S3_REGION", "LH_KEEP_LOCAL"):
        monkeypatch.delenv(name, raising=False)
    for name in ("LH_DATA_DIR", "LH_WORK_DIR", "LH_MANIFEST_DIR"):
        d = tmp_path / name.lower()
        d.mkdir()
        monkeypatch.setenv(name, str(d))
    return tmp_path


def _git(repo: Path, *args: str, date: str | None = None, author=("Ada Dev", "ada@example.org")):
    env = {**os.environ, "GIT_AUTHOR_NAME": author[0], "GIT_AUTHOR_EMAIL": author[1],
           "GIT_COMMITTER_NAME": "Maint Ainer", "GIT_COMMITTER_EMAIL": "maint@example.org",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


@pytest.fixture
def tiny_repo(tmp_path) -> Path:
    """A small repository with adds, edits, a delete, a binary, odd paths, a merge, tags and trailers."""
    r = tmp_path / "src-repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    (r / "src").mkdir()
    (r / "tests").mkdir()
    (r / "src" / "a.c").write_text("int a;\nint b;\nint c;\n")
    (r / "tests" / "test_a.py").write_text("def test():\n    pass\n")
    (r / "CONTRIBUTING.md").write_text("Contributions welcome.\n")
    (r / "logo.png").write_bytes(b"\x89PNG\x00\x01\x02binary")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "Initial import", date="2019-06-01T12:00:00+02:00")
    _git(r, "tag", "v0.9")

    (r / "src" / "a.c").write_text("int a;\nint B;\nint c;\nint d;\n")
    (r / "AGENTS.md").write_text("Run the tests before opening a PR.\n")
    (r / "weird\tname.txt").write_text("tab in the name\n")
    (r / "dócs").mkdir()
    (r / "dócs" / "ñ.md").write_text("unicode path\n")
    _git(r, "add", "-A")
    msg = ("Fix overflow in a\n\nLonger explanation of the fix.\n\n"
           "Signed-off-by: Ada Dev <ada@example.org>\nAssisted-by: Claude:claude-opus-5\n"
           "Co-authored-by: Copilot <copilot@github.com>")
    _git(r, "commit", "-q", "-m", msg, date="2021-03-01T09:30:00-05:00")
    _git(r, "tag", "-a", "v1.0", "-m", "release 1.0", date="2021-03-01T10:00:00-05:00")

    _git(r, "checkout", "-q", "-b", "feature")
    (r / "tests" / "test_a.py").unlink()
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "Drop old test", date="2022-01-01T00:00:00+00:00",
         author=("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com"))
    _git(r, "checkout", "-q", "main")
    (r / "CONTRIBUTING.md").write_text("Contributions welcome.\nAI-generated code must be disclosed.\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "Update contributing policy", date="2022-01-15T00:00:00+00:00")
    _git(r, "merge", "-q", "--no-ff", "feature", "-m", "Merge branch 'feature'", date="2022-02-01T00:00:00+00:00")
    (r / "src" / "a.c").chmod(0o755)
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "Make a.c executable", date="2023-05-05T00:00:00+00:00")
    return r
