from src.rag.runtime_policy import RAGRuntimePolicy


def test_windows_defaults_to_safe_subprocess_modes():
    policy = RAGRuntimePolicy.resolve("Windows", {})

    assert policy.is_windows is True
    assert policy.safe_delete_mode is True
    assert policy.subprocess_upsert_mode is True
    assert policy.subprocess_query_mode is True


def test_windows_runtime_flags_can_disable_each_safe_mode():
    policy = RAGRuntimePolicy.resolve(
        "Windows",
        {
            "EL_SECRETARIO_CHROMA_SAFE_DELETE": "false",
            "EL_SECRETARIO_RAG_SUBPROCESS_UPSERT": "0",
            "EL_SECRETARIO_RAG_SUBPROCESS_QUERY": "no",
        },
    )

    assert policy.is_windows is True
    assert policy.safe_delete_mode is False
    assert policy.subprocess_upsert_mode is False
    assert policy.subprocess_query_mode is False


def test_macos_and_ubuntu_keep_in_process_rag_modes_even_with_flags():
    flags = {
        "EL_SECRETARIO_CHROMA_SAFE_DELETE": "true",
        "EL_SECRETARIO_RAG_SUBPROCESS_UPSERT": "yes",
        "EL_SECRETARIO_RAG_SUBPROCESS_QUERY": "1",
    }

    for platform_name in ("Darwin", "Linux"):
        policy = RAGRuntimePolicy.resolve(platform_name, flags)
        assert policy.is_windows is False
        assert policy.safe_delete_mode is False
        assert policy.subprocess_upsert_mode is False
        assert policy.subprocess_query_mode is False
