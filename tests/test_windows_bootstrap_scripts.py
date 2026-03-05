from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_script(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_run_bat_prefers_python_312_or_311():
    content = _read_script("run.bat")
    assert r"%LocalAppData%\Programs\Python\Python312\python.exe" in content
    assert r"%LocalAppData%\Programs\Python\Python311\python.exe" in content
    assert "py -3.12 -m venv venv" in content
    assert "py -3.11 -m venv venv" in content


def test_reinstall_bat_prefers_python_312_or_311():
    content = _read_script("reinstall_and_run.bat")
    assert r"%LocalAppData%\Programs\Python\Python312\python.exe" in content
    assert r"%LocalAppData%\Programs\Python\Python311\python.exe" in content
    assert "py -3.12 -m venv venv" in content
    assert "py -3.11 -m venv venv" in content


def test_windows_scripts_validate_supported_python_range():
    expected = "sys.version_info[:2] <= (3,12)"
    for script in ("run.bat", "reinstall_and_run.bat"):
        content = _read_script(script)
        assert "(3,10) <= sys.version_info[:2]" in content
        assert expected in content
        assert "supports Python 3.10 to 3.12" in content
