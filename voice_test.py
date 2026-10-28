import pyttsx3
import time

print("Starting voice test...")

engine = pyttsx3.init()

engine.setProperty("rate", 150)
engine.setProperty("volume", 1.0)

print("Speaking now...")

engine.say("Hello. This is Smart Vision Navigation. Voice system is working.")
engine.runAndWait()

time.sleep(1)

print("Voice test completed.")