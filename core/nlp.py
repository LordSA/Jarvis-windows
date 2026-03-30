import re
import os

class IntentParser:
    def __init__(self, config_path="config/settings.json"):
        # Offline-only mode enabled
        pass

    def parse(self, text):
        """Parse text to determine intent and entities using local Regex patterns."""
        if not text:
            return None, {}
            
        text = text.lower()

        # Opening apps
        match = re.search(r"open\s+(.*)", text)
        if match:
            app_name = match.group(1).strip()
            return "open_app", {"app_name": app_name}
        
        # Searching the web
        match = re.search(r"search\s+for\s+(.*)", text)
        if match:
            query = match.group(1).strip()
            return "web_search", {"query": query}
            
        # Emailing
        match = re.search(r"send\s+email\s+to\s+(.*)", text)
        if match:
            recipient = match.group(1).strip()
            return "send_mail", {"to": recipient}
            
        # Add basic greeting intent
        if any(word in text for word in ["hello", "hi", "hey", "jarvis"]):
            return "greet", {}

        # Default fallback
        return None, {}
