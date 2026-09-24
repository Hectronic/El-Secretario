from unittest.mock import Mock

from src.api.server import LocalAPIServerThread


def test_api_thread_cleanup_releases_local_inference_resources(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    release = Mock()
    monkeypatch.setattr("src.api.server.release_local_inference_resources", release)

    LocalAPIServerThread().cleanup()

    release.assert_called_once_with()
