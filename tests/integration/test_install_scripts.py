import unittest
import subprocess
import os
import tempfile
import sys

class TestInstallScripts(unittest.TestCase):
    def test_linux_shortcut_uses_the_installed_icon_asset(self):
        """The user launcher must reference the PNG bundled under resources."""
        if sys.platform == "win32":
            self.skipTest("Linux desktop entry contract")

        script_path = os.path.join(os.getcwd(), "scripts", "install", "install.sh")
        with open(script_path, encoding="utf-8") as installer:
            script = installer.read()

        self.assertIn("Icon=$INSTALL_DIR/resources/logo.png", script)
        self.assertNotIn("Icon=$INSTALL_DIR/logo.png", script)

    def test_install_script_fails_gracefully_without_git(self):
        """Simulate missing git to test actionable error output (SPEC-021)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            is_windows = sys.platform == "win32"
            script_name = "install.bat" if is_windows else "install.sh"
            script_path = os.path.join(os.getcwd(), "scripts", "install", script_name)
            
            if not os.path.exists(script_path):
                self.skipTest(f"{script_name} not found")
                
            env = os.environ.copy()
            # Break PATH so git and python3 are not found
            env["PATH"] = ""
            
            if is_windows:
                cmd_exe = os.environ.get("COMSPEC", "C:\\Windows\\System32\\cmd.exe")
                cmd = [cmd_exe, "/c", script_path]
            else:
                cmd = ["/bin/bash", script_path]
                
            try:
                process = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True
                )
            except FileNotFoundError:
                # If cmd.exe or /bin/bash can't be found because we wiped PATH, skip
                self.skipTest(f"Could not launch shell on {sys.platform} without PATH")
                
            self.assertNotEqual(process.returncode, 0)
            
            output_to_check = process.stdout + process.stderr
            self.assertIn("Error: git is required", output_to_check)
            if is_windows:
                self.assertIn("Please install Git for Windows", output_to_check)
            else:
                self.assertIn("Install git via your package manager", output_to_check)
