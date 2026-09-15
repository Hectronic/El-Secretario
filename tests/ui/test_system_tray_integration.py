import unittest
import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer
from unittest.mock import MagicMock
from src.ui.system_tray_manager import SystemTrayManager

class TestSystemTrayIntegration(unittest.TestCase):
    def test_recording_badge_red_pixel(self):
        """Assert that the recording icon actually contains the red recording circle (SPEC-020 T005)."""
        app = QApplication.instance() or QApplication(sys.argv)
        manager = SystemTrayManager(None)
        
        manager._init_tray_icon()
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.skipTest("System tray not available in this environment")
        
        manager.set_recording_state(True)
        icon = manager._tray_icon.icon()
        self.assertFalse(icon.isNull(), "Icon should not be null")
        
        pixmap = icon.pixmap(32, 32)
        image = pixmap.toImage()
        
        has_red = False
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                if color.red() > 200 and color.green() < 50 and color.blue() < 50:
                    has_red = True
                    break
            if has_red:
                break
                
        self.assertTrue(has_red, "Recording badge must contain red pixels to indicate recording state")
