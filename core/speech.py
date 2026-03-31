import pyttsx3
import speech_recognition as sr
import json
import os
import sys

class SpeechManager:
    def __init__(self, config_path="config/settings.json"):
        self.config = self.load_config(config_path)
        
        # Initialize Speech Recognition first (Non-blocking)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.config.get('energy_threshold', 300)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.5
        self.recognizer.non_speaking_duration = 0.3
        self.recognizer.operation_timeout = 10
        self.mic_index = self.config.get('microphone_index', None)
        
        # Auto-detect Bluetooth Headsets (Lazy initialize)
        if self.mic_index is None:
            self.mic_index = self.discover_bluetooth_mic()
        
        # Check for PyAudio/Microphone availability
        self.has_microphone = True
        try:
            # Test if Microphone is available (requires PyAudio)
            import pyaudio
            p = pyaudio.PyAudio()
            # Explicitly check for valid device index
            if self.mic_index is not None:
                device_info = p.get_device_info_by_index(self.mic_index)
                print(f"DEBUG: Using Bluetooth device: {device_info['name']}")
            p.terminate()
        except Exception as e:
            print(f"Warning: Microphone initialization error: {e}. Falling back to text input.")
            self.has_microphone = False

        # Initialize Text-to-Speech last to avoid blocking mic stream
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

    def listen(self, timeout=5, phrase_limit=8):
        """Listen for audio input and return transcribed text with low latency."""
        if not self.has_microphone:
            return self.listen_text()

        try:
            # Re-instantiate Microphone on every loop to ensure stream is fresh
            # and avoid the 'NoneType' closure error from persistent instances.
            with sr.Microphone(device_index=self.mic_index) as source:
                # 1. Faster noise adjustment (once per session ideally, but 0.3s is fast)
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                
                # 2. Tighten silence detection to stop listening faster
                self.recognizer.pause_threshold = 0.5
                self.recognizer.non_speaking_duration = 0.3
                
                print(f"Listening on {self.mic_index if self.mic_index is not None else 'default'} mic...")
                # 3. Listen with tighter timeouts to prevent hanging
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                
                print("Processing...")
                try:
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
