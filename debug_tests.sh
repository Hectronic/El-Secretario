#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)

tests=(
    "tests/test_audio.py"
    "tests/test_worker.py"
    "tests/test_database.py"
    "tests/test_rag_engine.py"
    "tests/test_batch_process.py"
    "tests/test_calendar_button.py"
    "tests/test_calendar_logic.py"
    "tests/test_deletion.py"
    "tests/test_diarization_toggle.py"
    "tests/test_recording_flow.py"
    "tests/test_search.py"
    "tests/test_tab_context_menu.py"
    "tests/test_transcription_logging.py"
)

for test in "${tests[@]}"; do
    echo "Running $test..."
    ./venv/bin/python -m unittest "$test"
    if [ $? -ne 0 ]; then
        echo "Failed: $test"
        exit 1
    fi
done

echo "All tests passed individually."
