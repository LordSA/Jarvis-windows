import re
import os
try:
    import ollama
except Exception:
    ollama = None

class IntentParser:
    def __init__(self, config_path="config/settings.json"):
        # Offline LLM initialization via Ollama
        self.use_ollama = ollama is not None
        self.model = "llama3" # Default model
        if self.use_ollama:
            try:
                # Check if ollama is running/available
                ollama.list()
            except Exception:
                self.use_ollama = False
                print("Warning: Ollama not found. Using pattern matching.")
        else:
            self.use_ollama = False
            print("Warning: Ollama not found. Using pattern matching.")

    def parse(self, text):
        """Parse text into intent, entities, and actions."""
        if not text:
            return None, {}
            
        text = text.lower()

        # Offline LLM Logic
        if self.use_ollama:
            try:
                prompt = f"""
                You are Jarvis, an AI assistant. Analyze the user query and return a JSON response with 'intent' and 'entities'.
                Possible intents: system_status, vol_up, vol_down, vol_mute, media_toggle, media_next, media_prev, open_app, web_search, send_mail, system_power, greet, chat.
                
                Query: "{text}"
                
                Response format: {{"intent": "...", "entities": {{}}, "reply": "..."}}
                """
                response = ollama.generate(model=self.model, prompt=prompt)
                # Simple parsing of the response (can be improved with regex extract)
                import json
                res_content = response['response']
                # Search for json block if LLM adds preamble
                json_match = re.search(r'\{.*\}', res_content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    return data.get("intent"), data.get("entities", {}), data.get("reply")
            except Exception as e:
                print(f"Ollama Error: {e}. Falling back to patterns.")

        # Fallback to Pattern Matching
        # ... (rest of the existing logic)
        if any(word in text for word in ["how are you", "system status", "system health", "battery level", "cpu"]):
            return "system_status", {}, "Checking system status for you."
            
        if "volume up" in text:
            return "vol_up", {}, "Sure, increasing volume."
        if "volume down" in text:
            return "vol_down", {}, "Decreasing volume."
        if "mute" in text:
            return "vol_mute", {}, "System muted."
            
        if any(word in text for word in ["play", "pause", "resume"]):
            return "media_toggle", {}, "Toggling media."
        if "next" in text:
            return "media_next", {}, "Playing next track."
        if "previous" in text:
            return "media_prev", {}, "Playing previous track."

        match = re.search(r"open\s+(.*)", text)
        if match:
            app_name = match.group(1).replace("please", "").strip()
            return "open_app", {"app_name": app_name}, f"Opening {app_name}."

        return "chat", {}, None

    def parse_with_chat(self, text):
        """Specifically for conversational chat."""
        if self.use_ollama:
            try:
                response = ollama.chat(model=self.model, messages=[{'role': 'user', 'content': text}])
                return response['message']['content']
            except:
                return "I'm having trouble connecting to my local brain."
        return "I can't talk right now, I'm in pattern-only mode."
