import cv2
import pyttsx3
from ultralytics import YOLO
import time

# -----------------------------
# YOLO Model
# -----------------------------
model = YOLO("yolo11n.pt")

# -----------------------------
# Voice Engine
# -----------------------------
engine = pyttsx3.init()
engine.setProperty("rate", 150)

# -----------------------------
# Webcam
# -----------------------------
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():
    print("Camera open avvaledu!")
    exit()

print("Smart Vision Navigation Started!")
print("Q press chesthe close avutundi.")

# Object voice timing
last_spoken = {}
voice_delay = 3

while True:

    success, frame = camera.read()

    if not success:
        print("Frame read avvaledu!")
        break

    # YOLO detection
    results = model(frame, verbose=False)

    # Draw boxes
    annotated_frame = results[0].plot()

    current_time = time.time()

    # -----------------------------
    # Read EVERY detected object
    # -----------------------------
    for result in results:

        for box in result.boxes:

            confidence = float(box.conf[0])

            # Lower threshold
            if confidence < 0.25:
                continue

            class_id = int(box.cls[0])

            object_name = model.names[class_id]

            # -----------------------------
            # Console output
            # -----------------------------
            print(
                f"Detected: {object_name} "
                f"Confidence: {confidence:.2f}"
            )

            # -----------------------------
            # Voice output
            # -----------------------------
            previous_time = last_spoken.get(object_name, 0)

            if current_time - previous_time >= voice_delay:

                message = f"{object_name} detected"

                print("VOICE:", message)

                engine.say(message)
                engine.runAndWait()

                last_spoken[object_name] = current_time

    # -----------------------------
    # Show camera
    # -----------------------------
    cv2.imshow(
        "Smart Vision - AI Navigation",
        annotated_frame
    )

    # Q to exit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()