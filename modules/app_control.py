import subprocess
import os
import json
import pyautogui

class AppControl:
    def __init__(self, settings_path="config/settings.json"):
        self.settings_path = settings_path
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.settings_path, 'r') as f:
                self.apps = json.load(f).get('apps', {})
        except Exception:
            self.apps = {}

    def open_app(self, app_name):
        """Open an application by name with enhanced discovery."""
        app_name_lower = app_name.lower()
        app_path = self.apps.get(app_name_lower)
        
        # 1. Try pre-defined path from settings
        if app_path:
            try:
                subprocess.Popen(app_path, shell=True)
                return True
            except Exception:
                pass

        # 2. Universal "Start" fallback (Finds anything in Start Menu)
        try:
            print(f"Discovery: Using Start to launch {app_name}")
            # This triggers the Windows "Run" command or start menu search
            subprocess.Popen(f"start {app_name}", shell=True)
            return True
        except Exception as e:
            print(f"Error opening app: {e}")
            
        # 3. GUI fallback (Search menu)
        try:
            pyautogui.press('win')
            pyautogui.write(app_name, interval=0.1)
            pyautogui.press('enter')
            return True
        except Exception:
            return False
