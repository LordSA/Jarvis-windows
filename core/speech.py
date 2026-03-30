import pyttsx3
import speech_recognition as sr
import json
import os
import sys

class SpeechManager:
    def __init__(self, config_path="config/settings.json"):
        self.config = self.load_config(config_path)
        
        # Initialize Text-to-Speech
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', self.config.get('speech_rate', 150))
            self.tts_engine.setProperty('volume', self.config.get('volume', 1.0))
            self.tts_enabled = True
        except Exception as e:
            print(f"Warning: TTS initialization failed ({e}). Using text-only output.")
            self.tts_enabled = False
        
        # Initialize Speech Recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.config.get('energy_threshold', 300)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.5
        self.recognizer.operation_timeout = 10
        self.mic_index = self.config.get('microphone_index', None)
        
        # Auto-detect Bluetooth Headsets
        if self.mic_index is None:
            self.mic_index = self.discover_bluetooth_mic()
        
        # Check for PyAudio/Microphone availability
        self.has_microphone = True
        try:
            # Test if Microphone is available (requires PyAudio)
            with sr.Microphone(device_index=self.mic_index) as source:
                pass
        except (AttributeError, ImportError, Exception):
            print("Warning: PyAudio not found or Microphone not accessible. Falling back to text input.")
            self.has_microphone = False

    def load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def discover_bluetooth_mic(self):
        """Automatically search for Bluetooth Hands-Free devices."""
        try:
            mics = sr.Microphone.list_microphone_names()
            for i, name in enumerate(mics):
                # Common patterns for Bluetooth headsets in Windows
                if any(term in name.lower() for term in ["hands-free", "bluetooth", "headset", "pods", "buds"]):
                    print(f"Jarvis: Auto-detected Bluetooth Audio Device: {name}")
                    return i
        except Exception:
            pass
        return None

    def speak(self, text):
        """Convert text to speech."""
        print(f"Jarvis: {text}")
        if self.tts_enabled:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                pass

    def listen(self):
        """Listen for audio input and return transcribed text. Falls back to keyboard input if no mic."""
        if not self.has_microphone:
            return self.listen_text()

        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                print(f"Listening (Mic: {self.mic_index}) - Speak clearly...")
                # Bluetooth devices have higher latency, so we wait longer for silence
                self.recognizer.adjust_for_ambient_noise(source, duration=1.2)
                
                # Bluetooth audio often has brief 'silent' bursts, we increase pause threshold
                self.recognizer.pause_threshold = 1.0 
                
                # Listen with a generous timeout for Bluetooth connection wakeup
                audio = self.recognizer.listen(source, timeout=12, phrase_time_limit=15)
                
                print("Processing speech...")
                try:
                    query = self.recognizer.recognize_google(audio, language=self.config.get('recognition_language', 'en-US'))
                except sr.UnknownValueError:
                    return None
                except sr.RequestError:
                    print("Speech Service Error. Check Internet.")
                    return None
                
                print(f"User: {query}")
                return query.lower()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except Exception as e:
            # If Bluetooth device disconnected, retry with default index next time
            if "device" in str(e).lower():
                self.mic_index = None 
            print(f"Speech error: {e}. Falling back to text.")
            return self.listen_text()

    def listen_text(self):
        """Fallback method for keyboard input."""
        try:
            print("\n[Headless Mode] Type your command:")
            # Use raw_input/input based on environment, but here we're in Python 3
            query = input("User >> ").strip()
            if query:
                return query.lower()
        except EOFError:
            sys.exit(0)
        return None
