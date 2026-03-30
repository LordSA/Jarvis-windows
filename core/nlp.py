import re
import os

class IntentParser:
    def __init__(self, config_path="config/settings.json"):
        # Offline-only mode enabled
        pass

    def parse(self, text):
        """Parse text into intent, entities, and actions."""
        if not text:
            return None, {}
            
        text = text.lower()

        # 1. System Info & Control (High Priority)
        if any(word in text for word in ["how are you", "system status", "system health", "battery level", "cpu"]):
            return "system_status", {}
            
        if "volume up" in text:
            return "vol_up", {}
        if "volume down" in text:
            return "vol_down", {}
        if "mute" in text:
            return "vol_mute", {}
            
        if any(word in text for word in ["play", "pause", "resume"]):
            return "media_toggle", {}
        if "next" in text and "song" in text:
            return "media_next", {}
        if "previous" in text and "song" in text:
            return "media_prev", {}

        # 2. Universal App Launching 
        # Detect "open [app_name]"
        match = re.search(r"open\s+(.*)", text)
        if match:
            app_name = match.group(1).strip()
            return "open_app", {"app_name": app_name}
        
        # 3. Web Search
        match = re.search(r"search\s+for\s+(.*)", text)
        if match:
            query = match.group(1).strip()
            return "web_search", {"query": query}
            
        # 4. Emailing
        match = re.search(r"send\s+email\s+to\s+(.*)", text)
        if match:
            recipient = match.group(1).strip()
            return "send_mail", {"to": recipient}
            
        # 5. Power Commands
        if "shutdown" in text:
            return "system_power", {"mode": "shutdown"}
        if "restart" in text:
            return "system_power", {"mode": "restart"}

        # Greetings
        if any(word in text for word in ["hello", "hi", "jarvis"]):
            return "greet", {}

        return None, {}
