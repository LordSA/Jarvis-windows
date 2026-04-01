from PyQt6.QtCore import QThread, pyqtSignal
from .speech import SpeechManager
from .nlp import IntentParser
from modules.app_control import AppControl
from modules.web_control import WebControl
from modules.mail_control import MailControl
from modules.system_control import SystemControl
import time
import keyboard
import pyautogui
import re

class JarvisEngine(QThread):
    status_changed = pyqtSignal(str)
    query_heard = pyqtSignal(str)
    request_confirmation = pyqtSignal(str, object)

    def __init__(self, settings_path="config/settings.json"):
        super().__init__()
        self.speech_manager = SpeechManager(settings_path)
        self.intent_parser = IntentParser(settings_path)
        self.app_control = AppControl(settings_path)
        self.web_control = WebControl()
        self.mail_control = MailControl()
        self.sys_control = SystemControl()
        self.is_running = True
        self.keyboard_mode = False
        
        keyboard.add_hotkey('ctrl+alt+j', self.force_listen)
        keyboard.add_hotkey('shift+z', self.toggle_keyboard_mode)

    def toggle_keyboard_mode(self):
        self.keyboard_mode = not self.keyboard_mode
        mode_str = "Keyboards Only" if self.keyboard_mode else "Listening (Mic)"
        self.status_changed.emit(f"Mode: {mode_str}")
        self.speech_manager.speak(f"Switching to {mode_str} mode.")

    def force_listen(self):
        self.status_changed.emit("Listening (Hotkey)...")

    def run(self):
        self.status_changed.emit("Listening...")
        self.speech_manager.speak("Systems fully online. Ready for your commands.")
        
        while self.is_running:
            # Let the listening status update before we block
            if self.keyboard_mode:
                self.status_changed.emit("Waiting for command (Keyboard)...")
                query = self.speech_manager.listen_text()
            else:
                self.status_changed.emit("Listening...")
                # Reduced timeout to look for hotkeys more frequently
                query = self.speech_manager.listen(timeout=5, phrase_limit=10)
            
            if query:
                self.query_heard.emit(query)
                self.status_changed.emit("Analyzing...")
                # The updated nlp.py returns (intent, entities, reply)
                res = self.intent_parser.parse(query)
                if isinstance(res, tuple) and len(res) == 3:
                    intent, entities, reply = res
                else:
                    intent, entities = res
                    reply = None
                
                print(f"Jarvis Debug: Received query - '{query}'")
                print(f"Jarvis Debug: Parsed Intent - {intent}, Entities - {entities}")
                
                # Intent Execution Logic
                if intent == "greet":
                    self.speech_manager.speak("Hello! I'm here and listening.")
                
                elif intent == "system_status":
                    status = self.sys_control.get_system_status()
                    self.speech_manager.speak(status)
                
                elif intent == "vol_up":
                    self.sys_control.control_volume("vUp")
                    self.speech_manager.speak("Increasing volume.")
                elif intent == "vol_down":
                    self.sys_control.control_volume("vDown")
                    self.speech_manager.speak("Decreasing volume.")
                elif intent == "vol_mute":
                    self.sys_control.control_volume("vMute")
                    self.speech_manager.speak("Muting sound.")

                elif intent == "media_toggle":
                    self.sys_control.control_media("play_pause")
                    self.speech_manager.speak("Media toggled.")

                elif intent == "media_next":
                    self.sys_control.control_media("next")
                    self.speech_manager.speak("Next track.")

                elif intent == "media_prev":
                    self.sys_control.control_media("prev")
                    self.speech_manager.speak("Previous track.")

                elif intent == "open_app":
                    app_name = entities.get("app_name")
                    msg = f"Do you want me to launch {app_name}?"
                    print(f"Jarvis Debug: Requesting confirmation for app: {app_name}")
                    
                    self.speech_manager.speak(msg)
                    # Use specialized voice confirmation instead of just a popup
                    confirmed = self.get_voice_confirmation()
                    
                    print(f"Jarvis Debug: Voice confirmed {app_name}: {confirmed}")
                    if confirmed:
                        launched = self.app_control.open_app(app_name)
                        if launched:
                            self.speech_manager.speak(f"Launching {app_name}.")
                        else:
                            self.speech_manager.speak(f"I could not launch {app_name}.")
                
                elif intent == "chat" or reply:
                    chat_reply = reply if reply else self.intent_parser.parse_with_chat(query)
                    self.speech_manager.speak(chat_reply)
                
                else:
                    self.speech_manager.speak("I'm not sure how to help with that yet.")
            else:
                # Add a small sleep to prevent CPU spike in listen loops
                time.sleep(0.1)

            # Keep looking for keyboard shortcuts
            if keyboard.is_pressed('ctrl+c'):
                self.is_running = False
                break

    def get_voice_confirmation(self):
        """Get a yes/no confirmation via keyboard or microphone."""
        self.status_changed.emit("Confirm? (Yes/No)")
        for _ in range(2):
            if self.keyboard_mode:
                reply = self.speech_manager.listen_text()
            else:
                # Keep at least 5 seconds and allow short/clear confirmations.
                reply = self.speech_manager.listen(timeout=5, phrase_limit=5)
            if reply:
                print(f"Jarvis Debug: Confirmation Reply - {reply}")
                if self._is_affirmative(reply):
                    return True
                if self._is_negative(reply):
                    return False
                self.speech_manager.speak("Please say yes or no.")
        return False

    def _is_affirmative(self, text):
        normalized = re.sub(r"[^a-zA-Z\s]", " ", text.lower()).strip()
        words = set(normalized.split())
        affirm_words = {
            "yes", "y", "yeah", "yep", "yup", "ya", "sure", "ok", "okay", "confirm", "do", "go", "launch"
        }
        if words.intersection(affirm_words):
            return True

        # Accept near-miss transcriptions for short confirmations (e.g., "yas", "yess", "yep").
        for w in words:
            if w.startswith(("ye", "ya", "yu")) and len(w) <= 5:
                return True
            if self._is_close_word(w, ["yes", "yeah", "yep", "yup", "ok", "okay", "sure"], max_distance=1):
                return True

        return any(phrase in normalized for phrase in [
            "do it", "go ahead", "open it", "launch it", "yes please"
        ])

    def _is_negative(self, text):
        normalized = re.sub(r"[^a-zA-Z\s]", " ", text.lower()).strip()
        words = set(normalized.split())
        negative_words = {
            "no", "n", "nope", "nah", "cancel", "stop", "dont", "don't", "never"
        }
        if words.intersection(negative_words):
            return True

        for w in words:
            if self._is_close_word(w, ["no", "nope", "nah", "cancel", "stop"], max_distance=1):
                return True

        return any(phrase in normalized for phrase in [
            "not now", "do not", "don t", "no thanks"
        ])

    def _is_close_word(self, word, candidates, max_distance=1):
        if not word:
            return False
        return any(self._levenshtein(word, c) <= max_distance for c in candidates)

    def _levenshtein(self, a, b):
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)

        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, start=1):
            curr = [i]
            for j, cb in enumerate(b, start=1):
                ins = curr[j - 1] + 1
                delete = prev[j] + 1
                replace = prev[j - 1] + (0 if ca == cb else 1)
                curr.append(min(ins, delete, replace))
            prev = curr
        return prev[-1]

    def stop(self):
        self.is_running = False
        keyboard.unhook_all_hotkeys()
        self.quit()
        self.wait()
