import logging
import os
import platform


def subprocess_transcribe_entry(payload: dict, result_queue):
    """
    Run faster-whisper in an isolated process with minimal imports.
    This intentionally avoids importing torch/pyannote in this process.
    """
    # Import inside subprocess to keep parent process native libs isolated.
    from faster_whisper import WhisperModel

    if platform.system() == "Windows":
        os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        if payload["device"] == "cpu":
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1"
            os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
            if payload["compute_type"] == "float32":
                payload["compute_type"] = "int8_float32"

    try:
        cpu_threads = 1 if (platform.system() == "Windows" and payload["device"] == "cpu") else 4

        logging.info(
            "Subprocess transcription starting: model=%s device=%s compute_type=%s cpu_threads=%s",
            payload["model_size"],
            payload["device"],
            payload["compute_type"],
            cpu_threads,
        )

        model = WhisperModel(
            payload["model_size"],
            device=payload["device"],
            compute_type=payload["compute_type"],
            cpu_threads=cpu_threads,
        )
        segments, _info = model.transcribe(
            payload["audio_path"],
            beam_size=payload.get("beam_size", 5),
            language=payload.get("language"),
        )
        serialized_segments = [
            {"start": float(s.start), "end": float(s.end), "text": str(s.text)}
            for s in segments
        ]
        result_queue.put({"ok": True, "segments": serialized_segments})
    except Exception as e:
        result_queue.put({"ok": False, "error": str(e)})
