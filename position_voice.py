import cv2
import pyttsx3
from ultralytics import YOLO
import threading
import queue
import time


# ==========================================
# YOLO MODEL
# ==========================================

model = YOLO("yolo11n.pt")


# ==========================================
# VOICE QUEUE
# ==========================================

speech_queue = queue.Queue()


def voice_worker():

    engine = pyttsx3.init()

    engine.setProperty("rate", 150)

    while True:

        message = speech_queue.get()

        if message is None:
            break

        print("VOICE:", message)

        engine.say(message)
        engine.runAndWait()

        speech_queue.task_done()


# Start voice thread

voice_thread = threading.Thread(
    target=voice_worker,
    daemon=True
)

voice_thread.start()


# ==========================================
# CAMERA
# ==========================================

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():

    print("Camera open avvaledu!")

    exit()


print("Smart Vision - Position + Voice Started!")
print("Q press chesthe close avutundi.")


# ==========================================
# POSITION MEMORY
# ==========================================

previous_positions = {}

last_spoken_time = {}

VOICE_INTERVAL = 3


# ==========================================
# CONFIDENCE
# ==========================================

CONFIDENCE_THRESHOLD = 0.20


# ==========================================
# MAIN LOOP
# ==========================================

while True:

    success, frame = camera.read()

    if not success:

        print("Frame read avvaledu!")

        break


    height, width, _ = frame.shape


    # ======================================
    # LEFT / CENTER / RIGHT
    # ======================================

    left_limit = width // 3

    right_limit = (width * 2) // 3


    # ======================================
    # YOLO DETECTION
    # ======================================

    results = model(
        frame,
        verbose=False
    )


    annotated_frame = results[0].plot()


    # ======================================
    # OBJECTS
    # ======================================

    for result in results:

        for box in result.boxes:

            confidence = float(box.conf[0])

            if confidence < CONFIDENCE_THRESHOLD:

                continue


            # Object name

            class_id = int(box.cls[0])

            object_name = model.names[class_id]


            # Bounding box

            x1, y1, x2, y2 = box.xyxy[0].tolist()


            # Center X

            center_x = int((x1 + x2) / 2)


            # =================================
            # FIND POSITION
            # =================================

            if center_x < left_limit:

                position = "LEFT"

            elif center_x > right_limit:

                position = "RIGHT"

            else:

                position = "CENTER"


            # =================================
            # DISPLAY POSITION
            # =================================

            cv2.putText(

                annotated_frame,

                position,

                (
                    int(x1),
                    max(30, int(y1) - 10)
                ),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.8,

                (0, 255, 0),

                2
            )


            # =================================
            # OBJECT KEY
            # =================================

            object_key = object_name


            old_position = previous_positions.get(
                object_key
            )


            # =================================
            # VOICE
            # =================================

            message = None

            current_time = time.time()

            last_time = last_spoken_time.get(
                object_key,
                0
            )

            time_passed = (
                current_time - last_time
            )


            # =================================
            # FIRST DETECTION
            # =================================

            if old_position is None:

                if position == "LEFT":

                    message = (
                        f"{object_name} "
                        f"on your left"
                    )

                elif position == "RIGHT":

                    message = (
                        f"{object_name} "
                        f"on your right"
                    )

                else:

                    message = (
                        f"{object_name} ahead"
                    )


            # =================================
            # POSITION CHANGED
            # =================================

            elif old_position != position:

                if position == "LEFT":

                    message = (
                        f"{object_name} "
                        f"on your left"
                    )

                elif position == "RIGHT":

                    message = (
                        f"{object_name} "
                        f"on your right"
                    )

                else:

                    message = (
                        f"{object_name} ahead"
                    )


            # =================================
            # REPEAT AFTER 3 SECONDS
            # =================================

            elif time_passed >= VOICE_INTERVAL:

                if position == "LEFT":

                    message = (
                        f"{object_name} "
                        f"on your left"
                    )

                elif position == "RIGHT":

                    message = (
                        f"{object_name} "
                        f"on your right"
                    )

                else:

                    message = (
                        f"{object_name} ahead"
                    )


            # =================================
            # SEND VOICE
            # =================================

            if message is not None:

                print(
                    f"VOICE: {message}"
                )

                speech_queue.put(message)

                last_spoken_time[object_key] = (
                    current_time
                )


            # Update position

            previous_positions[object_key] = position


    # ======================================
    # DRAW LINES
    # ======================================

    cv2.line(

        annotated_frame,

        (left_limit, 0),

        (left_limit, height),

        (255, 255, 255),

        2
    )


    cv2.line(

        annotated_frame,

        (right_limit, 0),

        (right_limit, height),

        (255, 255, 255),

        2
    )


    # ======================================
    # LABELS
    # ======================================

    cv2.putText(

        annotated_frame,

        "LEFT",

        (20, 40),

        cv2.FONT_HERSHEY_SIMPLEX,

        1,

        (255, 255, 255),

        2
    )


    cv2.putText(

        annotated_frame,

        "CENTER",

        (
            width // 2 - 60,
            40
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        1,

        (255, 255, 255),

        2
    )


    cv2.putText(

        annotated_frame,

        "RIGHT",

        (
            width - 110,
            40
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        1,

        (255, 255, 255),

        2
    )


    # ======================================
    # SHOW CAMERA
    # ======================================

    cv2.imshow(

        "Smart Vision - Position + Voice",

        annotated_frame
    )


    # ======================================
    # Q TO CLOSE
    # ======================================

    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


# ==========================================
# CLOSE
# ==========================================

camera.release()

cv2.destroyAllWindows()

speech_queue.put(None)