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
                query = self.speech_manager.listen()
            
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
                        self.app_control.launch_app(app_name)
                        self.speech_manager.speak(f"Launching {app_name}.")
                
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
        """Specifically listen for Yes/No after a prompt."""
        self.status_changed.emit("Confirm? (Yes/No)")
        for _ in range(2): # Try twice
            # Faster timeout for confirmation
            reply = self.speech_manager.listen(timeout=5, phrase_limit=3)
            if reply:
                print(f"Jarvis Debug: Confirmation Reply - {reply}")
                if any(word in reply for word in ["yes", "yeah", "sure", "do it", "confirm"]):
                    return True
                if any(word in reply for word in ["no", "never", "cancel", "stop", "don't"]):
                    return False
        return False

    def stop(self):
        self.is_running = False
        keyboard.unhook_all_hotkeys()
        self.quit()
        self.wait()
