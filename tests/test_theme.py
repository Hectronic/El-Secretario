import unittest
from PyQt6.QtWidgets import QApplication
from src.ui.styles import apply_theme
import sys
import os

# Ensure QApplication exists
# We need to handle the case where an app instance already exists
app = QApplication.instance()
if not app:
    # Use valid argv or empty
    # Set plugin path if needed? usually fine.
    # Set headless mode for relevant platforms if needed.
    # For linux without display, this might crash if no xvfb.
    # But let's hop it works or is mocked.
    try:
        app = QApplication(sys.argv)
    except Exception as e:
        print(f"Failed to init QApplication: {e}")
        app = None

class TestTheme(unittest.TestCase):
    def setUp(self):
        if not app:
            self.skipTest("QApplication could not be initialized")

    def test_apply_theme_light(self):
        """Test applying light theme updates the global stylesheet."""
        apply_theme("Light")
        sheet = app.styleSheet()
        self.assertIn("background-color: #f5f5f5", sheet)
        self.assertIn("color: #333333", sheet)

    def test_apply_theme_dark(self):
        """Test applying dark theme updates the global stylesheet."""
        apply_theme("Dark")
        sheet = app.styleSheet()
        self.assertIn("background-color: #2b2b2b", sheet)
        self.assertIn("color: #eeeeee", sheet)

    def test_apply_theme_system(self):
        """Test applying System theme."""
        # Since we can't easily mock system theme easily here without extra deps,
        # just check it sets something.
        apply_theme("System")
        sheet = app.styleSheet()
        self.assertTrue("background-color" in sheet)

if __name__ == '__main__':
    unittest.main()
