from PyQt6.QtCore import QThread, pyqtSignal
from .speech import SpeechManager
from .nlp import IntentParser
from modules.app_control import AppControl
from modules.web_control import WebControl
from modules.mail_control import MailControl
import time

class JarvisEngine(QThread):
    """Background thread to handle voice listening and intent processing."""
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

    def run(self):
        """Main listening loop."""
        print("Engine started.")
        self.status_changed.emit("Listening...")
        
        while self.is_running:
            query = self.speech_manager.listen()
            
            if query:
                self.query_heard.emit(query)
                self.status_changed.emit("Thinking...")
                
                # Parse intent
                intent, entities = self.intent_parser.parse(query)
                
                if intent == "open_app":
                    app_name = entities.get("app_name")
                    msg = f"Do you want me to open {app_name}?"
                    # emit signal with message and the action to perform
                    def action(confirmed):
                        if confirmed:
                            success = self.app_control.open_app(app_name)
                            self.speech_manager.speak(f"Opening {app_name}") if success else self.speech_manager.speak("Failed to open app")
                        else:
                            self.speech_manager.speak("Okay, cancelling operation.")
                        self.status_changed.emit("Listening...")
                    
                    self.request_confirmation.emit(msg, action)

                elif intent == "web_search":
                    search_query = entities.get("query")
                    msg = f"Do you want me to search for {search_query}?"
                    def action(confirmed):
                        if confirmed:
                            self.web_control.search_google(search_query)
                            self.speech_manager.speak(f"Searching for {search_query}")
                        else:
                            self.speech_manager.speak("Okay, I won't search.")
                        self.status_changed.emit("Listening...")
                    self.request_confirmation.emit(msg, action)

                elif intent == "send_mail":
                    recipient = entities.get("to")
                    msg = f"Do you want me to send an email to {recipient}?"
                    def action(confirmed):
                        if confirmed:
                            self.mail_control.send_email(recipient)
                            self.speech_manager.speak(f"Opening mail for {recipient}")
                        else:
                            self.speech_manager.speak("No problem, stopping mail client.")
                        self.status_changed.emit("Listening...")
                    self.request_confirmation.emit(msg, action)

                else:
                    # Generic response
                    self.speech_manager.speak("I'm sorry, I don't know that command yet.")
                    self.status_changed.emit("Listening...")
            
            time.sleep(0.5)

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()
