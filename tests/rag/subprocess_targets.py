# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
import json
import os
import time


def write_success(payload, result_path):
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump({"ok": True, "result": payload.get("result", "done")}, f)


def write_operation_error(payload, result_path):
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump({"ok": False, "error": payload.get("error", "failed")}, f)


def remove_result_file(_payload, result_path):
    os.remove(result_path)


def crash_process(_payload, _result_path):
    raise RuntimeError("subprocess crash")


def sleep_past_timeout(_payload, _result_path):
    time.sleep(5)

