import pyautogui
import psutil
import platform
import os

class SystemControl:
    def __init__(self):
        pass

    def get_system_status(self):
        """Returns a string about the current system health."""
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        
        status = f"CPU is at {cpu}%. RAM usage is {ram}%."
        if battery:
            status += f" Battery level is {battery.percent}%."
        return status

    def control_volume(self, action):
        """Increase, decrease, or mute system volume."""
        if action == "vUp":
            pyautogui.press("volumeup")
            return "Volume increased."
        elif action == "vDown":
            pyautogui.press("volumedown")
            return "Volume decreased."
        elif action == "vMute":
            pyautogui.press("volumemute")
            return "Volume toggled."
        return "Unknown volume command."

    def control_media(self, action):
        """Play, pause, or skip media."""
        if action == "play_pause":
            pyautogui.press("playpause")
            return "Media toggled."
        elif action == "next":
            pyautogui.press("nexttrack")
            return "Skipped to next track."
        elif action == "prev":
            pyautogui.press("prevtrack")
            return "Returned to previous track."
        return "Unknown media command."

    def shutdown_system(self, mode="shutdown"):
        """Shutdown or restart Windows."""
        if mode == "shutdown":
            os.system("shutdown /s /t 5")
            return "System shutting down in 5 seconds."
        elif mode == "restart":
            os.system("shutdown /r /t 5")
            return "System restarting in 5 seconds."
        return "Invalid power mode."
