import subprocess
import os
import json

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
        """Open an application by name."""
        app_path = self.apps.get(app_name.lower())
        
        # fallback: try just using the app_name as executable if not in settings
        executable = app_path if app_path else f"{app_name}.exe"
        
        try:
            print(f"Opening: {executable}")
            # If path is specific or just the name, subprocess.Popen works
            subprocess.Popen(executable, shell=True)
            return True
        except Exception as e:
            print(f"Error opening app: {e}")
            return False
