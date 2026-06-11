"""Regression tests for DOMAIN_SKILL_MAP precision (false-positive Oracle fix).

Covers the Rex incident: a pure-Python project containing a single .sql file
(migration / SQLite schema / test fixture) was branded "Oracle" by the
`**/*.sql` glob and instructed to MANDATORY-invoke oracle-db-specialist on
every prompt, shadowing later entries like FastAPI.

Both copies of the detector are tested: session-start.py (SessionStart hook)
and raven-skill-reminder.py (UserPromptSubmit hook).
"""
import pathlib, tempfile, importlib.util

_ROOT = pathlib.Path(__file__).parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


session_start = _load("session_start_mod", "scripts/session-start.py")
reminder = _load("reminder_mod", "raven-core/raven-skill-reminder.py")
DETECTORS = [session_start.detect_domain, reminder.detect_domain]


def _fixture(builder) -> list:
    """Run builder(root) in a temp project dir, return both detectors' results."""
    results = []
    for detect in DETECTORS:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            builder(root)
            results.append(detect(root))
    return results


def test_sql_file_is_not_oracle() -> None:
    """A migrations/*.sql file + Python code must NOT detect Oracle (Rex bug)."""
    def build(root):
        (root / "migrations").mkdir()
        (root / "migrations" / "001_init.sql").write_text("CREATE TABLE t (id INT);")
        (root / "app.py").write_text("import asyncio\n")
    for skill, name, strength in _fixture(build):
        assert name != "Oracle", f"stray .sql branded Oracle ({skill}, {strength})"


def test_sql_does_not_shadow_fastapi() -> None:
    """fastapi in requirements + a stray .sql must detect FastAPI, not Oracle."""
    def build(root):
        (root / "schema.sql").write_text("CREATE TABLE t (id INT);")
        (root / "requirements.txt").write_text("fastapi==0.115.0\nuvicorn\n")
    for skill, name, strength in _fixture(build):
        assert name == "FastAPI" and strength == "strong", (skill, name, strength)


def test_tnsnames_is_oracle() -> None:
    """tnsnames.ora marker MUST detect Oracle (strong)."""
    def build(root):
        (root / "tnsnames.ora").write_text("PROD = (DESCRIPTION=...)")
    for skill, name, strength in _fixture(build):
        assert (name, strength) == ("Oracle", "strong"), (skill, name, strength)


def test_oracle_drivers_in_requirements() -> None:
    """cx_Oracle (legacy) and oracledb (modern) in requirements MUST detect Oracle."""
    for driver in ("cx_Oracle==8.3.0", "oracledb>=2.0"):
        def build(root, d=driver):
            (root / "requirements.txt").write_text(f"{d}\n")
        for skill, name, strength in _fixture(build):
            assert (name, strength) == ("Oracle", "strong"), (driver, name, strength)


def test_plsql_packages_are_oracle() -> None:
    """.pkb / .pks PL/SQL package files remain a strong Oracle signal."""
    def build(root):
        (root / "billing.pkb").write_text("CREATE OR REPLACE PACKAGE BODY billing ...")
    for skill, name, strength in _fixture(build):
        assert (name, strength) == ("Oracle", "strong"), (skill, name, strength)


def test_single_generic_dir_is_weak() -> None:
    """A lone k8s/ dir is advisory (weak), not a mandatory detection."""
    def build(root):
        (root / "k8s").mkdir()
    for skill, name, strength in _fixture(build):
        assert (name, strength) == ("Kubernetes", "weak"), (skill, name, strength)


def test_two_weak_dirs_agree_to_strong() -> None:
    """k8s/ + helm/ together upgrade Kubernetes to strong."""
    def build(root):
        (root / "k8s").mkdir()
        (root / "helm").mkdir()
    for skill, name, strength in _fixture(build):
        assert (name, strength) == ("Kubernetes", "strong"), (skill, name, strength)


def test_charts_dir_is_not_kubernetes() -> None:
    """A JS charting assets folder named charts/ must not trigger Kubernetes."""
    def build(root):
        (root / "charts").mkdir()
        (root / "charts" / "revenue.js").write_text("export const chart = {};")
    for skill, name, strength in _fixture(build):
        assert name is None, (skill, name, strength)


def test_generic_template_yaml_is_not_aws() -> None:
    """A generic template.yaml without CloudFormation content is not AWS."""
    def build(root):
        (root / "template.yaml").write_text("kind: scaffold\nname: demo\n")
    for skill, name, strength in _fixture(build):
        assert name != "AWS", (skill, name, strength)


def test_sam_template_yaml_is_aws() -> None:
    """A template.yaml with AWS:: resources MUST detect AWS (strong)."""
    def build(root):
        (root / "template.yaml").write_text(
            "Resources:\n  Fn:\n    Type: AWS::Serverless::Function\n")
    for skill, name, strength in _fixture(build):
        assert (name, strength) == ("AWS", "strong"), (skill, name, strength)


if __name__ == "__main__":
    failures = 0
    for fn_name, fn in sorted(globals().items()):
        if fn_name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {fn_name}")
            except AssertionError as e:
                failures += 1
                print(f"❌ {fn_name}: {e}")
    raise SystemExit(failures)
