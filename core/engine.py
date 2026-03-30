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

    def run(self):
        self.status_changed.emit("Listening...")
        self.speech_manager.speak("Systems fully online.")
        
        while self.is_running:
            query = self.speech_manager.listen()
            
            if query:
                self.query_heard.emit(query)
                self.status_changed.emit("Analyzing...")
                intent, entities = self.intent_parser.parse(query)
                
                # Intent Execution Logic
                if intent == "greet":
                    self.speech_manager.speak("How can I help you, sir?")
                
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

                elif intent == "open_app":
                    app_name = entities.get("app_name")
                    msg = f"Do you want me to launch {app_name}?"
                    def action(confirmed, aname=app_name):
                        if confirmed:
                            self.app_control.open_app(aname)
                            self.speech_manager.speak(f"Launching {aname}")
                        self.status_changed.emit("Listening...")
                    self.request_confirmation.emit(msg, action)

                elif intent == "web_search":
                    s_query = entities.get("query")
                    msg = f"Search Google for {s_query}?"
                    def action(confirmed, sq=s_query):
                        if confirmed:
                            self.web_control.search_google(sq)
                            self.speech_manager.speak(f"Searching for {sq}")
                        self.status_changed.emit("Listening...")
                    self.request_confirmation.emit(msg, action)

                elif intent == "system_power":
                    mode = entities.get("mode")
                    msg = f"Danger: Perform system {mode}?"
                    def action(confirmed, m=mode):
                        if confirmed:
                            self.sys_control.shutdown_system(m)
                        self.status_changed.emit("Listening...")
                    self.request_confirmation.emit(msg, action)

                self.status_changed.emit("Listening...")
            time.sleep(0.1)

    def stop(self):
        self.is_running = False
        keyboard.unhook_all_hotkeys()
        self.quit()
        self.wait()
