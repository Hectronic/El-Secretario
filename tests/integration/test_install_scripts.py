import unittest
import subprocess
import os
import tempfile
import sys

class TestInstallScripts(unittest.TestCase):
    def test_install_script_fails_gracefully_without_git(self):
        """Simulate missing git to test actionable error output (SPEC-021)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(os.getcwd(), "install.sh")
            if not os.path.exists(script_path):
                self.skipTest("install.sh not found")
                
            env = os.environ.copy()
            # break PATH so git and python3 are not found
            env["PATH"] = ""
            
            process = subprocess.run(
                ["/bin/bash", script_path],
                env=env,
                capture_output=True,
                text=True
            )
            self.assertNotEqual(process.returncode, 0)
            self.assertIn("Error: git is required", process.stderr)
            self.assertIn("Install git via your package manager", process.stderr)
