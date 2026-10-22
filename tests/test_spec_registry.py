"""Keep the living feature inventory and its local evidence navigable."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"


def _features():
    return sorted(path for path in SPECS.glob("[0-9][0-9][0-9]-*") if path.is_dir())


def _local_targets(path):
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
        if not re.match(r"^(https?:|mailto:|#)", target):
            yield path.parent / target.split("#", 1)[0]


def test_every_feature_has_artifacts_request_and_current_inventory():
    index = (SPECS / "README.md").read_text()
    requests = (SPECS / "REQUESTS.md").read_text()
    current = (SPECS / "CURRENT.md").read_text()
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
        text = (ROOT / name).read_text()
        assert "specs/REQUESTS.md" in text
        assert "specs/CURRENT.md" in text
