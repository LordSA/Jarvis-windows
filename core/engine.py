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
        
        keyboard.add_hotkey('ctrl+alt+j', self.force_listen)

    def force_listen(self):
        self.status_changed.emit("Listening (Hotkey)...")

    def get_voice_confirmation(self):
        """Ultra-fast confirmation listening."""
        self.status_changed.emit("Confirm? (Yes/No)")
        # Tighter listening window for confirm
        reply = self.speech_manager.listen(timeout=3, phrase_limit=2)
        if reply:
            print(f"DEBUG: Confirm Reply: {reply}")
            if any(word in reply for word in ["yes", "yeah", "sure", "ok", "yep"]):
                return True
        return False

    def run(self):
        self.status_changed.emit("Listening...")
        self.speech_manager.speak("Systems fully online. Ready for your commands.")
        
        while self.is_running:
            # Let the listening status update before we block
            self.status_changed.emit("Listening...")
            time.sleep(0.1) 
            query = self.speech_manager.listen()
            
            if query:
                self.query_heard.emit(query)
                self.status_changed.emit("Analyzing...")
                intent, entities = self.intent_parser.parse(query)
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
                        self.app_control.open_app(app_name)
                        self.speech_manager.speak(f"Launching {app_name}")
                    else:
                        self.speech_manager.speak("Action cancelled.")
                        
                    self.status_changed.emit("Listening...")

                elif intent == "web_search":
                    s_query = entities.get("query")
                    msg = f"Search Google for {s_query}?"
                    self.speech_manager.speak(msg)
                    if self.get_voice_confirmation():
                        self.web_control.search_google(s_query)
                        self.speech_manager.speak(f"Searching for {s_query}")
                    self.status_changed.emit("Listening...")

                elif intent == "system_power":
                    mode = entities.get("mode")
                    msg = f"Perform system {mode}?"
                    self.speech_manager.speak(msg)
                    if self.get_voice_confirmation():
                        self.sys_control.shutdown_system(mode)
                    self.status_changed.emit("Listening...")

                self.status_changed.emit("Listening...")
            time.sleep(0.1)

    def stop(self):
        self.is_running = False
        keyboard.unhook_all_hotkeys()
        self.quit()
        self.wait()
