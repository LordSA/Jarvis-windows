import re

class IntentParser:
    def __init__(self, config_path="config/settings.json"):
        # We can add more refined logic or load from a config if needed
        pass

    def parse(self, text):
        """Parse text to determine intent and entities."""
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
            
        # Default fallback
        return None, {}
