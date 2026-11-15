"""Path rules: which changed files are tests, docs, vendored, generated, CI or build.

Rules are regular expressions over the repo-relative path. Each project config can
add patterns per class:

    paths:
      test: ["^src/check/"]
      vendored: ["^ext/"]

These are first-pass rules. They are validated on hand-labelled samples before any
test-to-code share is reported.
"""

from __future__ import annotations

import polars as pl

DEFAULT_RULES: dict[str, list[str]] = {
    "test": [
        r"(^|/)(tests?|testing|testsuite|test-?suite|unittests?|__tests__|spec|specs|t)/",
        r"(^|/)test_[^/]*\.py$",
        r"_test\.(py|go|rs|c|cc|cpp|rb|exs?)$",
        r"(^|/)[^/]*[._-](test|spec)\.(js|jsx|ts|tsx|mjs|cjs)$",
        r"(Test|Tests|IT)\.(java|kt|scala|cs)$",
        r"_spec\.rb$",
        r"(^|/)(fixtures|testdata|test-data|test_data)/",
    ],
    "docs": [
        r"(^|/)(docs?|documentation|man|manual|website|site)/",
        r"\.(md|rst|adoc|txt|texi|texinfo|pod)$",
        r"(^|/)(README|CHANGES|CHANGELOG|NEWS|HISTORY|AUTHORS|CONTRIBUTORS|THANKS)([._-][^/]*)?$",
    ],
    "vendored": [
        r"(^|/)(vendor|vendored|third[_-]?party|3rdparty|external|extern|deps|node_modules|bundled)/",
    ],
    "generated": [
        r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|poetry\.lock|uv\.lock|Gemfile\.lock|"
        r"composer\.lock|go\.sum|Pipfile\.lock|bun\.lockb?|flake\.lock)$",
        r"\.min\.(js|css)$",
        r"\.(pb\.go|pb\.cc|pb\.h|_pb2\.py|pb2_grpc\.py)$",
        r"(^|/)(dist|build|generated|gen|autogen)/",
        r"(^|/)(configure|aclocal\.m4|Makefile\.in|config\.h\.in)$",
        r"\.snap$",
    ],
    "ci": [
        r"^\.github/workflows/", r"^\.gitlab-ci\.yml$", r"^\.circleci/", r"^\.travis\.yml$",
        r"(^|/)azure-pipelines[^/]*\.ya?ml$", r"(^|/)Jenkinsfile$", r"^\.buildkite/", r"^\.cirrus\.yml$",
        r"^\.ci/", r"^ci/",
    ],
    "build": [
        r"(^|/)(CMakeLists\.txt|Makefile|GNUmakefile|meson\.build|meson_options\.txt|configure\.ac|"
        r"BUILD|BUILD\.bazel|WORKSPACE|MODULE\.bazel|BUCK|SConstruct|setup\.py|setup\.cfg|pyproject\.toml|"
        r"package\.json|Cargo\.toml|go\.mod|pom\.xml|build\.gradle(\.kts)?|settings\.gradle(\.kts)?|"
        r"Dockerfile|Containerfile|Rakefile|Gemfile|[^/]*\.gemspec|[^/]*\.cabal)$",
        r"\.(cmake|bzl|gni?|mk)$",
    ],
}

CLASSES = list(DEFAULT_RULES)


def rules(overrides: dict | None = None) -> dict[str, str]:
    """One combined regex per class, defaults plus project additions."""
    out = {}
    for cls, pats in DEFAULT_RULES.items():
        extra = list((overrides or {}).get(cls) or [])
        out[cls] = "|".join(f"(?:{p})" for p in pats + extra)
    return out


def flag_exprs(path_col: str = "path", overrides: dict | None = None) -> list[pl.Expr]:
    """Polars expressions adding is_<class> boolean columns, plus top_dir and ext."""
    col = pl.col(path_col)
    exprs = [col.str.contains(rx).fill_null(False).alias(f"is_{cls}") for cls, rx in rules(overrides).items()]
    exprs.append(
        pl.when(col.str.contains("/")).then(col.str.split("/").list.first()).otherwise(pl.lit("")).alias("top_dir")
    )
    exprs.append(col.str.extract(r"\.([A-Za-z0-9_+-]{1,12})$", 1).str.to_lowercase().alias("ext"))
    return exprs


def add_flags(df: pl.DataFrame, path_col: str = "path", overrides: dict | None = None) -> pl.DataFrame:
    return df.with_columns(flag_exprs(path_col, overrides))
