from src.worker_components.lifecycle import TerminalOutcomeEmitter, TerminalStatus


def test_terminal_outcome_is_emitted_once_and_has_application_contract():
    emitter = TerminalOutcomeEmitter("job-1")

    outcome = emitter.complete(TerminalStatus.TIMED_OUT, user_message="Timed out", retryable=True)

    assert outcome.payload() == {
        "status": "timed_out", "operation_id": "job-1", "user_message": "Timed out",
        "retryable": True, "preserved_work": True,
    }
    assert emitter.complete(TerminalStatus.FAILED, user_message="later") is None
