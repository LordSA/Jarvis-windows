import pyttsx3
import speech_recognition as sr
import json
import os
import sys
import threading
import concurrent.futures

class SpeechManager:
    def __init__(self, config_path="config/settings.json"):
        self.config = self.load_config(config_path)
        self.tts_lock = threading.Lock()
        
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
        self.recognizer.energy_threshold = self.config.get('energy_threshold', 300)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.4
        self.recognizer.operation_timeout = 8
        self.mic_candidates = self.build_mic_candidates()
        self.mic_index = self.mic_candidates[0] if self.mic_candidates else None
        self.consecutive_timeouts = 0
        self.mic_failure_counts = {}
        self.preferred_phrase_timeout = self.config.get('phrase_time_limit', 10)
        self.preferred_listen_timeout = max(5, self.config.get('listen_timeout', 5))
        
        # Check for PyAudio/Microphone availability
        self.has_microphone = True
        try:
            # Test if at least one microphone is available (requires PyAudio)
            self.mic_index = self.select_working_microphone()
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
                # We look for "hands-free" which is the standard Windows profile for bidirectional Bluetooth audio
                if "hands-free" in name.lower() or "headset" in name.lower():
                    # Check if the name contains common headset brands or 'hands-free'
                    if any(term in name.lower() for term in ["buds", "pods", "hands-free", "bt", "bluetooth"]):
                        print(f"Jarvis: Auto-detected Bluetooth Audio Device: {name}")
                        return i
        except Exception:
            pass
        return None

    def _mic_label(self, mic_index):
        if mic_index is None:
            return "Default"
        try:
            mics = sr.Microphone.list_microphone_names()
            if 0 <= int(mic_index) < len(mics):
                return f"{mic_index} ({mics[int(mic_index)]})"
        except Exception:
            pass
        return str(mic_index)

    def build_mic_candidates(self):
        """Build a prioritized microphone list: configured -> bluetooth -> default -> others."""
        candidates = []
        configured = self.config.get('microphone_index', None)
        if configured is not None:
            candidates.append(configured)

        bluetooth = self.discover_bluetooth_mic()
        if bluetooth is not None:
            candidates.append(bluetooth)

        # None means default system microphone in speech_recognition.
        candidates.append(None)

        try:
            mic_count = len(sr.Microphone.list_microphone_names())
            for i in range(mic_count):
                candidates.append(i)
        except Exception:
            pass

        # Preserve order and remove duplicates.
        deduped = []
        for c in candidates:
            if c not in deduped:
                deduped.append(c)
        return deduped

    def select_working_microphone(self):
        """Pick the first microphone candidate that can be opened."""
        for candidate in self.mic_candidates:
            try:
                with sr.Microphone(device_index=candidate):
                    pass
                if candidate is None:
                    print("Jarvis: Using default system microphone.")
                else:
                    print(f"Jarvis: Using microphone index {candidate}.")
                return candidate
            except Exception:
                continue
        raise RuntimeError("No usable microphone device found")

    def rotate_microphone(self):
        """Move to the next microphone candidate when current one is not responsive."""
        if not self.mic_candidates:
            return
        if self.mic_index not in self.mic_candidates:
            self.mic_index = self.mic_candidates[0]
            return

        current_pos = self.mic_candidates.index(self.mic_index)
        for offset in range(1, len(self.mic_candidates) + 1):
            candidate = self.mic_candidates[(current_pos + offset) % len(self.mic_candidates)]
            try:
                with sr.Microphone(device_index=candidate):
                    pass
                self.mic_index = candidate
                print(f"Jarvis: Switching to microphone {self._mic_label(candidate)}.")
                return
            except Exception:
                continue

    def _recognize_google_with_timeout(self, audio, language, timeout_seconds=6):
        """Bound online recognition so network calls cannot freeze the main loop."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.recognizer.recognize_google, audio, language=language)
            try:
                return future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                return None

    def speak(self, text):
        """Convert text to speech."""
        print(f"Jarvis: {text}")
        if self.tts_enabled:
            try:
                with self.tts_lock:
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
                    with self.tts_lock:
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
                except Exception:
                    pass

    def listen(self, timeout=None, phrase_limit=None):
        """Listen for audio input and return transcribed text. Falls back to keyboard input if no mic."""
        if not self.has_microphone:
            return self.listen_text()

        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                # Keep calibration short to avoid the appearance of a hang.
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Set a default timeout if none provided to prevent indefinite hanging
                listen_timeout = timeout if timeout is not None else self.preferred_listen_timeout
                listen_phrase_limit = phrase_limit if phrase_limit is not None else self.preferred_phrase_timeout

                print(f"Listening (Mic: {self._mic_label(self.mic_index)})...")
                try:
                    audio = self.recognizer.listen(source, timeout=listen_timeout, phrase_time_limit=listen_phrase_limit)
                    self.consecutive_timeouts = 0
                    self.mic_failure_counts[self.mic_index] = 0
                except sr.WaitTimeoutError:
                    self.consecutive_timeouts += 1
                    self.mic_failure_counts[self.mic_index] = self.mic_failure_counts.get(self.mic_index, 0) + 1
                    print(f"Jarvis: No speech detected on {self._mic_label(self.mic_index)}.")

                    # Bluetooth mics often expose a non-capturing profile; rotate quickly.
                    if self.mic_index is not None and self.mic_failure_counts[self.mic_index] >= 1:
                        self.rotate_microphone()
                    elif self.consecutive_timeouts >= 2:
                        self.consecutive_timeouts = 0
                        self.rotate_microphone()
                    return None
                except Exception as e:
                    print(f"Listen error: {e}")
                    self.rotate_microphone()
                    return None

                print("Processing...")
                try:
                    language = self.config.get('recognition_language', 'en-US')
                    query = self._recognize_google_with_timeout(audio, language=language, timeout_seconds=6)
                    if query:
                        print(f"User: {query}")
                        return query.lower()

                    # If online recognition timed out, try offline mode immediately.
                    try:
                        offline_query = self.recognizer.recognize_sphinx(audio)
                        if offline_query:
                            print(f"User (offline): {offline_query}")
                            return offline_query.lower()
                    except Exception:
                        pass

                    print("Jarvis: Speech heard but not recognized.")
                    return None
                except sr.UnknownValueError:
                    # For short utterances like "yes"/"no", offline decode can still succeed.
                    try:
                        offline_query = self.recognizer.recognize_sphinx(audio)
                        if offline_query:
                            print(f"User (offline): {offline_query}")
                            return offline_query.lower()
                    except Exception:
                        pass
                    return None
                except sr.RequestError:
                    # Fallback to offline recognizer when network recognition is unavailable.
                    try:
                        offline_query = self.recognizer.recognize_sphinx(audio)
                        if offline_query:
                            print(f"User (offline): {offline_query}")
                            return offline_query.lower()
                    except Exception:
                        pass
                    return None
                    
        except Exception as e:
            # Handle Bluetooth disconnects / permission issues
            msg = str(e).lower()
            if "device" in msg or "invalid" in msg or "busy" in msg:
                print(f"DEBUG: Hardware error detected ({e}). Resetting to default mic.")
                self.mic_index = None
                self.rotate_microphone()
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
