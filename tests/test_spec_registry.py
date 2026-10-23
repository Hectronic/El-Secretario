"""Keep the living feature inventory and its local evidence navigable."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"


def _features():
    return sorted(path for path in SPECS.glob("[0-9][0-9][0-9]-*") if path.is_dir())


def _local_targets(path):
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if not re.match(r"^(https?:|mailto:|#)", target):
            yield path.parent / target.split("#", 1)[0]


def test_every_feature_has_artifacts_request_and_current_inventory():
    index = (SPECS / "README.md").read_text(encoding="utf-8")
    requests = (SPECS / "REQUESTS.md").read_text(encoding="utf-8")
    current = (SPECS / "CURRENT.md").read_text(encoding="utf-8")
    for feature in _features():
        assert f"{feature.name}/spec.md" in index
        assert f"{feature.name}/spec.md" in requests
        assert f"{feature.name}/spec.md" in current
        for artifact in ("spec.md", "plan.md", "tasks.md"):
            assert (feature / artifact).is_file()
    request_ids = re.findall(r"^\| (REQ-\d+(?:\.\d+)?) \|", requests, re.MULTILINE)
    assert request_ids
    assert len(request_ids) == len(set(request_ids))


def test_registry_and_current_evidence_links_exist():
    for name in ("README.md", "REQUESTS.md", "CURRENT.md"):
        path = SPECS / name
        for target in _local_targets(path):
            assert target.exists(), f"{path}: {target}"
    for feature in _features():
        spec = feature / "spec.md"
        for target in _local_targets(spec):
            assert target.exists(), f"{spec}: {target}"


def test_all_readme_languages_link_to_requests_and_current_functionality():
    for name in ("README.md", "README_ES.md", "README_AST.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "specs/REQUESTS.md" in text
        assert "specs/CURRENT.md" in text


def test_registry_checks_work_with_utf8_mode_disabled():
    import os
    import subprocess
    import sys

    env = dict(os.environ, LC_ALL="C", PYTHONCOERCECLOCALE="0")
    code = (
        "import runpy; checks = runpy.run_path('tests/test_spec_registry.py'); "
        "checks['test_every_feature_has_artifacts_request_and_current_inventory'](); "
        "checks['test_registry_and_current_evidence_links_exist'](); "
        "checks['test_all_readme_languages_link_to_requests_and_current_functionality']()"
    )
    result = subprocess.run(
        [sys.executable, "-X", "utf8=0", "-c", code], cwd=ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", timeout=20,
    )
    assert result.returncode == 0, result.stderr
