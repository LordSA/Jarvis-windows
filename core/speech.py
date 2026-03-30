import pyttsx3
import speech_recognition as sr
import json
import os

class SpeechManager:
    def __init__(self, config_path="config/settings.json"):
        self.config = self.load_config(config_path)
        
        # Initialize Text-to-Speech
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', self.config.get('speech_rate', 150))
        self.tts_engine.setProperty('volume', self.config.get('volume', 1.0))
        
        # Initialize Speech Recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.config.get('energy_threshold', 300)
        self.recognizer.dynamic_energy_threshold = True

    def load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def speak(self, text):
        """Convert text to speech."""
        print(f"Jarvis: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def listen(self):
        """Listen for audio input and return transcribed text."""
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("Recognizing...")
                query = self.recognizer.recognize_google(audio, language=self.config.get('recognition_language', 'en-US'))
                print(f"User: {query}")
                return query.lower()
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return None
            except sr.RequestError:
                print("Network error.")
                return None
            except Exception as e:
                print(f"Speech error: {e}")
                return None
