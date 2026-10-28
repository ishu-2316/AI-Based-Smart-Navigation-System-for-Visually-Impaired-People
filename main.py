import cv2
import time
import threading
import queue
import pyttsx3
import pythoncom
from ultralytics import YOLO


# ============================================================
# SMART VISION NAVIGATION SYSTEM
# Continuous Object + Position + Voice Guidance
# ============================================================

MODEL_PATH = "yolo11n.pt"

CONFIDENCE = 0.40

# Same object/location announcement repeat interval
ANNOUNCE_INTERVAL = 3.0

# Every announcement is spoken 3 times
REPEAT_COUNT = 3

# Small gap between repetitions
REPEAT_DELAY = 0.5


# ============================================================
# VOICE SYSTEM
# ============================================================

voice_queue = queue.Queue()

stop_voice = threading.Event()


def voice_worker():

    pythoncom.CoInitialize()

    engine = pyttsx3.init()

    engine.setProperty("rate", 150)
    engine.setProperty("volume", 1.0)

    while not stop_voice.is_set():

        try:
            message = voice_queue.get(timeout=0.2)

        except queue.Empty:
            continue

        print("🔊 SPEAKING:", message)

        # Speak 3 times
        for i in range(REPEAT_COUNT):

            if stop_voice.is_set():
                break

            engine.say(message)
            engine.runAndWait()

            if i < REPEAT_COUNT - 1:
                time.sleep(REPEAT_DELAY)

        voice_queue.task_done()

    engine.stop()

    pythoncom.CoUninitialize()


# ============================================================
# SPEAK
# ============================================================

def speak(message):

    # Don't allow unlimited old messages
    # Remove old waiting messages

    try:

        while True:

            old = voice_queue.get_nowait()
            voice_queue.task_done()

    except queue.Empty:
        pass


    try:

        voice_queue.put_nowait(message)

    except queue.Full:

        pass


# ============================================================
# POSITION
# ============================================================

def get_position(center_x, frame_width):

    left_boundary = frame_width / 3

    right_boundary = frame_width * 2 / 3

    if center_x < left_boundary:

        return "left"

    elif center_x > right_boundary:

        return "right"

    else:

        return "ahead"


# ============================================================
# FRIENDLY NAMES
# ============================================================

def friendly_name(name):

    names = {

        "person": "person",
        "cell phone": "phone",
        "bottle": "bottle",
        "chair": "chair",
        "laptop": "laptop",
        "keyboard": "keyboard",
        "mouse": "mouse",
        "book": "book",
        "remote": "remote",
        "backpack": "bag",
        "handbag": "bag",
        "suitcase": "suitcase",

        "car": "car",
        "bus": "bus",
        "truck": "truck",
        "motorcycle": "bike",
        "bicycle": "bicycle",

        "dog": "dog",
        "cat": "cat",

        "cup": "cup",
        "bowl": "bowl",
        "banana": "banana",
        "apple": "apple",
        "orange": "orange",

        "umbrella": "umbrella",
        "scissors": "scissors",
        "clock": "clock",
        "vase": "vase",
        "toothbrush": "toothbrush",

        "tv": "television",
        "dining table": "table",
        "tie": "tie",

    }

    return names.get(name, name)


# ============================================================
# VOICE MESSAGE
# ============================================================

def create_message(object_name, position):

    if position == "left":

        return f"{object_name} on your left"

    elif position == "right":

        return f"{object_name} on your right"

    else:

        return f"{object_name} ahead"


# ============================================================
# START PROGRAM
# ============================================================

print()
print("==============================================")
print("     SMART VISION NAVIGATION SYSTEM")
print("==============================================")
print()

print("Loading YOLO model...")

model = YOLO(MODEL_PATH)

print("YOLO model loaded successfully!")

print()
print("Starting voice system...")


# ============================================================
# START VOICE THREAD
# ============================================================

voice_thread = threading.Thread(
    target=voice_worker,
    daemon=True
)

voice_thread.start()

time.sleep(1)

print("Voice system started.")

print()
print("Starting camera...")


# ============================================================
# CAMERA
# ============================================================

camera = cv2.VideoCapture(
    0,
    cv2.CAP_DSHOW
)


if not camera.isOpened():

    print("ERROR: Camera could not be opened.")

    stop_voice.set()

    raise SystemExit


print("Camera started successfully!")

print()
print("==============================================")
print("       SMART VISION IS ACTIVE")
print("==============================================")
print()
print("Press Q to stop.")
print()


# ============================================================
# OBJECT MEMORY
# ============================================================

# Stores:
#
# object name
# position
# last time spoken

last_announced = {}


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        success, frame = camera.read()

        if not success:

            print("Camera frame error.")

            break


        frame_height, frame_width = frame.shape[:2]


        # ====================================================
        # LEFT / CENTER / RIGHT LINES
        # ====================================================

        left_line = int(frame_width / 3)

        right_line = int(frame_width * 2 / 3)


        cv2.line(
            frame,
            (left_line, 0),
            (left_line, frame_height),
            (255, 255, 255),
            2
        )


        cv2.line(
            frame,
            (right_line, 0),
            (right_line, frame_height),
            (255, 255, 255),
            2
        )


        # ====================================================
        # REGION LABELS
        # ====================================================

        cv2.putText(
            frame,
            "LEFT",
            (25, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            "CENTER",
            (left_line + 20, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            "RIGHT",
            (right_line + 20, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )


        # ====================================================
        # YOLO
        # ====================================================

        results = model(
            frame,
            conf=CONFIDENCE,
            verbose=False
        )


        # Current objects in this frame
        current_objects = set()


        # ====================================================
        # PROCESS DETECTIONS
        # ====================================================

        for result in results:

            for box in result.boxes:

                confidence = float(box.conf[0])


                if confidence < CONFIDENCE:

                    continue


                # ------------------------------------------------
                # OBJECT NAME
                # ------------------------------------------------

                class_id = int(box.cls[0])

                original_name = model.names[class_id]

                object_name = friendly_name(
                    original_name
                )


                # ------------------------------------------------
                # BOUNDING BOX
                # ------------------------------------------------

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )


                # ------------------------------------------------
                # CENTER
                # ------------------------------------------------

                center_x = int(
                    (x1 + x2) / 2
                )

                center_y = int(
                    (y1 + y2) / 2
                )


                # ------------------------------------------------
                # POSITION
                # ------------------------------------------------

                position = get_position(
                    center_x,
                    frame_width
                )


                # ------------------------------------------------
                # DRAW BOX
                # ------------------------------------------------

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (255, 255, 255),
                    2
                )


                # ------------------------------------------------
                # CENTER POINT
                # ------------------------------------------------

                cv2.circle(
                    frame,
                    (center_x, center_y),
                    6,
                    (255, 255, 255),
                    -1
                )


                # ------------------------------------------------
                # LABEL
                # ------------------------------------------------

                label = (
                    f"{object_name} "
                    f"{confidence:.2f} "
                    f"[{position}]"
                )


                cv2.putText(
                    frame,
                    label,
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2
                )


                # =================================================
                # VOICE STATE
                # =================================================

                state_key = (
                    f"{object_name}_{position}"
                )


                current_objects.add(
                    state_key
                )


                current_time = time.time()


                # =================================================
                # CHECK WHEN TO SPEAK
                # =================================================

                should_speak = False


                # -------------------------------------------------
                # NEW OBJECT OR NEW POSITION
                # -------------------------------------------------

                if state_key not in last_announced:

                    should_speak = True


                else:

                    previous_time = (
                        last_announced[state_key]
                    )


                    # ------------------------------------------------
                    # CONTINUOUS REPEAT
                    # ------------------------------------------------

                    if (
                        current_time - previous_time
                        >= ANNOUNCE_INTERVAL
                    ):

                        should_speak = True


                # =================================================
                # SPEAK
                # =================================================

                if should_speak:

                    message = create_message(
                        object_name,
                        position
                    )


                    print(
                        "Detected:",
                        object_name,
                        "| Position:",
                        position,
                        "| Confidence:",
                        round(confidence, 2)
                    )


                    speak(message)


                    last_announced[state_key] = (
                        current_time
                    )


        # ====================================================
        # REMOVE OLD STATES
        # ====================================================

        # This allows an object to be treated as NEW
        # when it disappears and later comes back.

        keys_to_remove = []


        for key in last_announced:

            if key not in current_objects:

                old_time = last_announced[key]

                if time.time() - old_time > 2:

                    keys_to_remove.append(key)


        for key in keys_to_remove:

            del last_announced[key]


        # ====================================================
        # STATUS
        # ====================================================

        cv2.putText(
            frame,
            "SMART VISION ACTIVE",
            (20, frame_height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # ====================================================
        # SHOW CAMERA
        # ====================================================

        cv2.imshow(
            "Smart Vision Navigation",
            frame
        )


        # ====================================================
        # Q
        # ====================================================

        key = cv2.waitKey(1) & 0xFF


        if key == ord("q"):

            break


# ============================================================
# CLOSE
# ============================================================

finally:

    print()
    print("Closing Smart Vision Navigation...")


    camera.release()

    cv2.destroyAllWindows()


    stop_voice.set()


    print("System stopped.")