from types import SimpleNamespace
from unittest.mock import Mock

from src import resource_cleanup


def test_release_local_inference_resources_collects_python_and_cuda_caches(monkeypatch):
    collect = Mock(return_value=7)
    cuda = SimpleNamespace(
        is_available=Mock(return_value=True),
        empty_cache=Mock(),
        ipc_collect=Mock(),
    )
    monkeypatch.setattr(resource_cleanup.gc, "collect", collect)
    monkeypatch.setattr(resource_cleanup, "_load_torch", lambda: SimpleNamespace(cuda=cuda))

    assert resource_cleanup.release_local_inference_resources() == 7

    collect.assert_called_once_with()
    cuda.empty_cache.assert_called_once_with()
    cuda.ipc_collect.assert_called_once_with()


def test_release_local_inference_resources_is_safe_without_cuda(monkeypatch):
    cuda = SimpleNamespace(is_available=Mock(return_value=False))
    monkeypatch.setattr(resource_cleanup, "_load_torch", lambda: SimpleNamespace(cuda=cuda))

    resource_cleanup.release_local_inference_resources()

    cuda.is_available.assert_called_once_with()


def test_release_local_inference_resources_does_not_import_torch_just_to_clean(monkeypatch):
    monkeypatch.delitem(resource_cleanup.sys.modules, "torch", raising=False)

    resource_cleanup.release_local_inference_resources()

    assert "torch" not in resource_cleanup.sys.modules


def test_release_local_inference_resources_swallows_cuda_cleanup_failure(monkeypatch):
    cuda = SimpleNamespace(
        is_available=Mock(return_value=True),
        empty_cache=Mock(side_effect=RuntimeError("driver is shutting down")),
        ipc_collect=Mock(),
    )
    monkeypatch.setattr(resource_cleanup, "_load_torch", lambda: SimpleNamespace(cuda=cuda))

    resource_cleanup.release_local_inference_resources()

    cuda.empty_cache.assert_called_once_with()
    cuda.ipc_collect.assert_not_called()
