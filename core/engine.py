from PyQt6.QtCore import QThread, pyqtSignal
from .speech import SpeechManager
from .nlp import IntentParser
from modules.app_control import AppControl
from modules.web_control import WebControl
from modules.mail_control import MailControl
import time
import keyboard
import pyautogui

class JarvisEngine(QThread):
    """Background thread to handle voice listening, hotkeys, and intent processing."""
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
        self.is_running = True
        
        # Setup hotkeys
        keyboard.add_hotkey('ctrl+alt+j', self.force_listen)
        keyboard.add_hotkey('ctrl+alt+s', self.stop_listening)

    def force_listen(self):
        print("Hotkey: Force Listening...")
        self.status_changed.emit("Listening (Hotkey)...")

    def stop_listening(self):
        print("Hotkey: Emergency Stop...")
        self.is_running = False

    def run(self):
        """Main listening loop."""
        print("Engine started.")
        self.status_changed.emit("Listening...")
        # Friendly greeting
        self.speech_manager.speak("System initialized. I am online and ready.")
        
        while self.is_running:
            query = self.speech_manager.listen()
            
            if query:
                self.query_heard.emit(query)
                self.status_changed.emit("Analyzing...")
                
                # Parse intent
                intent, entities = self.intent_parser.parse(query)
                
                if intent == "greet":
                    self.speech_manager.speak("Hello! How can I assist you today?")
                    self.status_changed.emit("Listening...")

                elif intent == "open_app":
                    app_name = entities.get("app_name")
                    msg = f"Confirmation: Launch {app_name}?"
                    def action(confirmed):
                        if confirmed:
                            success = self.app_control.open_app(app_name)
                            if success:
                                self.speech_manager.speak(f"Launching {app_name}.")
                            else:
                                self.speech_manager.speak("I couldn't find that application.")
                        else:
                            self.speech_manager.speak("Action aborted.")
                        self.status_changed.emit("Listening...")
                    self.request_confirmation.emit(msg, action)

                elif intent == "web_search":
                    search_query = entities.get("query")
                    msg = f"Confirmation: Search Google for '{search_query}'?"
                    def action(confirmed):
                        if confirmed:
                            self.web_control.search_google(search_query)
                            self.speech_manager.speak(f"Searching for {search_query} now.")
                        else:
                            self.speech_manager.speak("Search cancelled.")
                        self.status_changed.emit("Listening...")
                    self.request_confirmation.emit(msg, action)

                elif intent == "send_mail":
                    recipient = entities.get("to")
                    msg = f"Confirmation: Compose email to {recipient}?"
                    def action(confirmed):
                        if confirmed:
                            self.mail_control.send_email(recipient)
                            self.speech_manager.speak(f"Opening your mail client.")
                        else:
                            self.speech_manager.speak("Email cancelled.")
                        self.status_changed.emit("Listening...")
                    self.request_confirmation.emit(msg, action)

                else:
                    self.status_changed.emit("Listening...")
            
            time.sleep(0.1)

    def stop(self):
        self.is_running = False
        keyboard.unhook_all_hotkeys()
        self.quit()
        self.wait()
