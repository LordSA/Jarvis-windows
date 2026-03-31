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
            
            # Switch to Female Voice (Zira)
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if "zira" in voice.name.lower() or "female" in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            self.tts_enabled = True
        except Exception as e:
            print(f"Warning: TTS initialization failed ({e}). Using text-only output.")
            self.tts_enabled = False
        
        # Initialize Speech Recognition
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000  # Default higher for noisy environments, auto-adjust follows
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.5
        self.recognizer.operation_timeout = None  # Don't timeout the operation itself
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
                # Use a fresh engine instance to avoid "NoneType" error or hanging/blocking issues
                # especially when called from keyboard or different threads
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                # If engine is corrupted (e.g. by thread conflicts), recreate it
                try:
                    self.tts_engine = pyttsx3.init()
                    # Re-apply voice settings
                    voices = self.tts_engine.getProperty('voices')
                    for voice in voices:
                        if "zira" in voice.name.lower() or "female" in voice.name.lower():
                            self.tts_engine.setProperty('voice', voice.id)
                            break
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                except:
                    pass

    def listen(self, timeout=None, phrase_limit=None):
        """Listen for audio input and return transcribed text. Falls back to keyboard input if no mic."""
        if not self.has_microphone:
            return self.listen_text()

        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                print(f"Listening (Mic: {self.mic_index}) - Speak clearly...")
                # Automatic noise adjustment
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
                
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                
                print("Processing speech...")
                try:
                    # Use faster offline-capable recognition or tighter Google API
                    query = self.recognizer.recognize_google(audio, language=self.config.get('recognition_language', 'en-US'))
                    if query:
                        print(f"User: {query}")
                        return query.lower()
                    return None
                except (sr.UnknownValueError, sr.RequestError):
                    return None
                    
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except Exception as e:
            # Handle Bluetooth disconnects / permission issues
            msg = str(e).lower()
            if "device" in msg or "invalid" in msg or "busy" in msg:
                print(f"DEBUG: Hardware error detected ({e}). Resetting to default mic.")
                self.mic_index = None 
            else:
                print(f"DEBUG: Listen Error: {e}")
            return None

    def listen_text(self):
        """Fallback method for keyboard input."""
        try:
            print("\n[Headless Mode] Type your command:")
            query = input("User >> ").strip()
            if query:
                return query.lower()
        except EOFError:
            sys.exit(0)
        return None
