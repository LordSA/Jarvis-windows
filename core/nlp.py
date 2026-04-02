import re
import os
import json
import time
import subprocess
try:
    import ollama
except Exception:
    ollama = None

class IntentParser:
    KNOWN_INTENTS = {
        "system_status",
        "vol_up",
        "vol_down",
        "vol_mute",
        "media_toggle",
        "media_next",
        "media_prev",
        "open_app",
        "web_search",
        "send_mail",
        "system_power",
        "greet",
        "chat",
    }

    INTENT_ALIASES = {
        "open application": "open_app",
        "open_application": "open_app",
        "launch app": "open_app",
        "launch_app": "open_app",
        "launch application": "open_app",
        "start app": "open_app",
        "start application": "open_app",
        "volume_up": "vol_up",
        "volume_down": "vol_down",
        "volume_mute": "vol_mute",
        "play_pause": "media_toggle",
    }

    def __init__(self, config_path="config/settings.json"):
        self.config = self._load_config(config_path)
        self.ollama_client = None
        self.ollama_ready = False
        self.last_ollama_retry = 0
        self.retry_cooldown_seconds = 10
        self.model = self.config.get("ollama_model", "llama3")
        self.ollama_host = self.config.get("ollama_host") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
        self.auto_start_ollama = self.config.get("auto_start_ollama", True)
        self.use_ollama = self.config.get("use_ollama", True) and (ollama is not None)

        if self.use_ollama:
            self._connect_ollama(force=True)
        else:
            print("Warning: Ollama python client unavailable or disabled. Using pattern matching.")

    def _load_config(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _extract_model_names(self, list_result):
        models = []
        raw_models = None
        if isinstance(list_result, dict):
            raw_models = list_result.get("models", [])
        else:
            raw_models = getattr(list_result, "models", [])

        for item in raw_models or []:
            if isinstance(item, dict):
                name = item.get("model") or item.get("name")
            else:
                name = getattr(item, "model", None) or getattr(item, "name", None)
            if name:
                models.append(name)
        return models

    def _start_ollama_server(self):
        if not self.auto_start_ollama:
            return False

        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW

            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            return True
        except Exception:
            return False

    def _connect_ollama(self, force=False):
        if not self.use_ollama:
            return False

        now = time.time()
        if not force and (now - self.last_ollama_retry) < self.retry_cooldown_seconds:
            return self.ollama_ready

        self.last_ollama_retry = now
        try:
            self.ollama_client = ollama.Client(host=self.ollama_host)
            listed = self.ollama_client.list()
            model_names = self._extract_model_names(listed)
            if not model_names:
                print("Warning: Ollama connected, but no models found. Run: ollama pull llama3")
                self.ollama_ready = False
                return False

            if self.model not in model_names:
                original_model = self.model
                self.model = model_names[0]
                print(f"Warning: Model '{original_model}' not found. Using '{self.model}' instead.")

            self.ollama_ready = True
            return True
        except Exception:
            started = self._start_ollama_server()
            if started:
                # Give the service a short time to initialize.
                for _ in range(3):
                    time.sleep(1)
                    try:
                        self.ollama_client = ollama.Client(host=self.ollama_host)
                        listed = self.ollama_client.list()
                        model_names = self._extract_model_names(listed)
                        if model_names:
                            if self.model not in model_names:
                                self.model = model_names[0]
                            self.ollama_ready = True
                            return True
                    except Exception:
                        continue

            self.ollama_ready = False
            print(
                "Warning: Ollama service is not accessible. "
                "Start it with 'ollama serve' and ensure a model exists (example: 'ollama pull llama3')."
            )
            return False

    def _normalize_text(self, text):
        if text is None:
            return ""
        # Collapse repeated whitespace and trim to avoid blank-looking queries.
        return " ".join(str(text).strip().split())

    def _canonicalize_intent(self, intent):
        if not intent:
            return None
        key = self._normalize_text(intent).lower().replace("-", "_")
        return self.INTENT_ALIASES.get(key, key)

    def _extract_json_object(self, content):
        if not content:
            return None

        candidate = self._normalize_text(content)
        # Prefer fenced JSON if model returns markdown.
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL | re.IGNORECASE)
        if fenced:
            candidate = fenced.group(1)

        # Otherwise grab the first non-greedy JSON-looking object.
        if not candidate.startswith("{"):
            match = re.search(r"\{.*?\}", content, re.DOTALL)
            if not match:
                return None
            candidate = match.group(0)

        try:
            return json.loads(candidate)
        except Exception:
            return None

    def _extract_app_name(self, text):
        normalized = self._normalize_text(text).lower()
        if not normalized:
            return None

        match = re.search(r"(?:open|launch|start)\s+(.+)", normalized)
        if not match:
            return None

        app_name = match.group(1)
        # Remove common filler words that break app matching.
        app_name = re.sub(r"\b(please|the|app|application|for me|now|jarvis)\b", " ", app_name)
        app_name = self._normalize_text(app_name)

        invalid = {"", "it", "this", "that"}
        if app_name in invalid:
            return None
        return app_name

    def parse(self, text):
        """Parse text into intent, entities, and actions."""
        text = self._normalize_text(text)
        if not text:
            return None, {}

        text = text.lower()

        # Offline LLM Logic
        if self.use_ollama and self._connect_ollama():
            try:
                prompt = f"""
                You are Jarvis, an AI assistant. Analyze the user query and return a JSON response with 'intent' and 'entities'.
                Possible intents: system_status, vol_up, vol_down, vol_mute, media_toggle, media_next, media_prev, open_app, web_search, send_mail, system_power, greet, chat.
                
                Query: "{text}"
                
                Response format: {{"intent": "...", "entities": {{}}, "reply": "..."}}
                """
                response = self.ollama_client.generate(model=self.model, prompt=prompt)
                res_content = response.get("response", "") if isinstance(response, dict) else ""
                data = self._extract_json_object(res_content)
                if data:
                    intent = self._canonicalize_intent(data.get("intent"))
                    entities = data.get("entities", {})
                    if not isinstance(entities, dict):
                        entities = {}
                    reply = data.get("reply")
                    if isinstance(reply, str):
                        reply = self._normalize_text(reply)

                    # Accept only known intents; unknown intents should not short-circuit into chat.
                    if intent in self.KNOWN_INTENTS:
                        if intent == "open_app" and not entities.get("app_name"):
                            extracted_app = self._extract_app_name(text)
                            if extracted_app:
                                entities["app_name"] = extracted_app
                        return intent, entities, reply
            except Exception as e:
                self.ollama_ready = False
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

        app_name = self._extract_app_name(text)
        if app_name:
            return "open_app", {"app_name": app_name}, f"Opening {app_name}."

        return "chat", {}, None

    def parse_with_chat(self, text):
        """Specifically for conversational chat."""
        text = self._normalize_text(text)
        if not text:
            return "I did not catch that. Please say that again."

        if self.use_ollama and self._connect_ollama():
            try:
                response = self.ollama_client.chat(model=self.model, messages=[{'role': 'user', 'content': text}])
                content = ""
                if isinstance(response, dict):
                    message = response.get("message", {})
                    if isinstance(message, dict):
                        content = message.get("content", "")
                content = self._normalize_text(content)
                if content:
                    return content
                return "I heard you, but got an empty response. Please try again."
            except Exception:
                self.ollama_ready = False
                return "I'm having trouble connecting to my local brain."
        return "I can't talk right now, I'm in pattern-only mode."
