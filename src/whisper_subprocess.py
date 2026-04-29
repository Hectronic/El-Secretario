import gc
import logging
import os
import platform


def _serialize_segments(segments):
    return [
        {"start": float(s.start), "end": float(s.end), "text": str(s.text)}
        for s in segments
    ]


def _normalize_openai_whisper_model_name(model_size: str) -> str:
    if model_size in ("large-v3", "large-v2"):
        return "large"
    return model_size


def _prepare_audio_for_openai_whisper(audio_path: str):
    import numpy as np
    import soundfile as sf

    audio, sample_rate = sf.read(audio_path, always_2d=False)
    audio = np.asarray(audio, dtype=np.float32)

    if audio.ndim > 1:
        audio = np.mean(audio, axis=1).astype(np.float32)

    target_sr = 16000
    if int(sample_rate) != target_sr:
        if audio.size == 0:
            return audio
        duration_seconds = len(audio) / float(sample_rate)
        target_len = max(1, int(round(duration_seconds * target_sr)))
        src_x = np.linspace(0.0, duration_seconds, num=len(audio), endpoint=False)
        dst_x = np.linspace(0.0, duration_seconds, num=target_len, endpoint=False)
        audio = np.interp(dst_x, src_x, audio).astype(np.float32)

    return audio


def _create_sherpa_onnx_recognizer(*, sherpa_onnx_module, model_config: dict, language: str):
    common_kwargs = {
        "tokens": model_config["tokens"],
        "num_threads": 2,
        "sample_rate": 16000,
        "feature_dim": 80,
        "decoding_method": "greedy_search",
        "debug": False,
    }
    model_type = model_config["type"]

    if model_type == "transducer":
        return sherpa_onnx_module.OfflineRecognizer.from_transducer(
            encoder=model_config["encoder"],
            decoder=model_config["decoder"],
            joiner=model_config["joiner"],
            **common_kwargs,
        )
    if model_type == "paraformer":
        return sherpa_onnx_module.OfflineRecognizer.from_paraformer(
            paraformer=model_config["model"],
            **common_kwargs,
        )
    if model_type == "nemo-ctc":
        return sherpa_onnx_module.OfflineRecognizer.from_nemo_ctc(
            model=model_config["model"],
            **common_kwargs,
        )
    if model_type == "wenet-ctc":
        return sherpa_onnx_module.OfflineRecognizer.from_wenet_ctc(
            model=model_config["model"],
            **common_kwargs,
        )
    if model_type == "tdnn-ctc":
        return sherpa_onnx_module.OfflineRecognizer.from_tdnn_ctc(
            model=model_config["model"],
            **common_kwargs,
        )
    if model_type == "whisper":
        return sherpa_onnx_module.OfflineRecognizer.from_whisper(
            encoder=model_config["encoder"],
            decoder=model_config["decoder"],
            tokens=model_config["tokens"],
            num_threads=1,
            decoding_method="greedy_search",
            debug=False,
            language=language or "",
            task="transcribe",
            tail_paddings=-1,
        )

    raise RuntimeError(f"Unsupported Sherpa-ONNX model type: {model_type}")


def _transcribe_faster_whisper(payload: dict):
    from faster_whisper import WhisperModel

    if platform.system() == "Windows":
        os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        if payload["device"] == "cpu":
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1"
            os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
            if payload["compute_type"] == "float32":
                payload["compute_type"] = "int8_float32"

    cpu_threads = 1 if (platform.system() == "Windows" and payload["device"] == "cpu") else 4
    logging.info(
        "Subprocess transcription starting: backend=faster-whisper model=%s device=%s compute_type=%s cpu_threads=%s",
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
    return _serialize_segments(segments)


def _transcribe_openai_whisper(payload: dict):
    import whisper

    fallback_model = _normalize_openai_whisper_model_name(payload["model_size"])
    logging.info(
        "Subprocess transcription starting: backend=openai-whisper model=%s",
        fallback_model,
    )
    model = whisper.load_model(fallback_model)
    try:
        audio_data = _prepare_audio_for_openai_whisper(payload["audio_path"])
        result = model.transcribe(audio_data, language=payload.get("language"))
    except Exception as audio_prepare_error:
        logging.warning(
            "openai-whisper local audio loading failed (%s). Falling back to ffmpeg path mode.",
            audio_prepare_error,
        )
        try:
            result = model.transcribe(payload["audio_path"], language=payload.get("language"))
        except FileNotFoundError as ffmpeg_missing_error:
            raise RuntimeError(
                "FFmpeg is not installed or not available in PATH. "
                "Install FFmpeg system-wide (for example C:\\ffmpeg\\bin in PATH) "
                "and retry transcription."
            ) from ffmpeg_missing_error
    segments = result.get("segments") or []
    return [
        {
            "start": float(s.get("start", 0.0)),
            "end": float(s.get("end", 0.0)),
            "text": str(s.get("text", "")),
        }
        for s in segments
    ]


def _transcribe_sherpa_onnx(payload: dict):
    try:
        import numpy as np
        import sherpa_onnx
        import soundfile as sf
    except ImportError as e:
        raise RuntimeError(
            "sherpa-onnx support requires the 'sherpa-onnx' package to be installed."
        ) from e

    logging.info(
        "Subprocess transcription starting: backend=sherpa-onnx model_type=%s",
        payload["model_config"].get("type"),
    )
    recognizer = _create_sherpa_onnx_recognizer(
        sherpa_onnx_module=sherpa_onnx,
        model_config=payload["model_config"],
        language=payload.get("language"),
    )

    audio, sample_rate = sf.read(payload["audio_path"], always_2d=False)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1).astype(np.float32)

    stream = recognizer.create_stream()
    stream.accept_waveform(sample_rate, audio)
    recognizer.decode_streams([stream])
    result = getattr(stream, "result", None)
    text = str(getattr(result, "text", "") or "").strip()

    if not text:
        return []

    duration = len(audio) / float(sample_rate) if sample_rate else 0.0
    return [{"start": 0.0, "end": float(duration), "text": text}]


def subprocess_transcribe_entry(payload: dict, result_queue):
    """
    Run transcription in an isolated process.
    This keeps large native backends from retaining memory in the parent process.
    """
    backend = payload.get("backend", "faster-whisper")

    try:
        if backend == "faster-whisper":
            segments = _transcribe_faster_whisper(payload)
        elif backend == "openai-whisper":
            segments = _transcribe_openai_whisper(payload)
        elif backend == "sherpa-onnx":
            segments = _transcribe_sherpa_onnx(payload)
        else:
            raise RuntimeError(f"Unsupported transcription backend: {backend}")

        result_queue.put({"ok": True, "segments": segments})
    except Exception as e:
        result_queue.put({"ok": False, "error": str(e)})
    finally:
        gc.collect()
