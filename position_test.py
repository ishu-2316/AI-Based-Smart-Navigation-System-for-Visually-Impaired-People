import cv2
from ultralytics import YOLO

# Load YOLO model
model = YOLO("yolo11n.pt")

# Open webcam
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():
    print("Camera open avvaledu!")
    exit()

print("Position Detection Started!")
print("Q press chesthe close avutundi.")

while True:

    success, frame = camera.read()

    if not success:
        print("Frame read avvaledu!")
        break

    # Get frame dimensions
    height, width, _ = frame.shape

    # Divide screen into 3 sections
    left_limit = width // 3
    right_limit = (width * 2) // 3

    # YOLO detection
    results = model(frame, verbose=False)

    # Draw detection boxes
    annotated_frame = results[0].plot()

    # Check every detected object
    for result in results:

        for box in result.boxes:

            confidence = float(box.conf[0])

            # Ignore very low confidence
            if confidence < 0.25:
                continue

            # Object name
            class_id = int(box.cls[0])
            object_name = model.names[class_id]

            # Bounding box coordinates
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # Center X coordinate
            center_x = int((x1 + x2) / 2)

            # Determine position
            if center_x < left_limit:
                position = "LEFT"

            elif center_x > right_limit:
                position = "RIGHT"

            else:
                position = "CENTER"

            # Print result in terminal
            print(
                f"{object_name} -> {position} "
                f"(Confidence: {confidence:.2f})"
            )

            # Display position on screen
            cv2.putText(
                annotated_frame,
                position,
                (int(x1), int(y1) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

    # Draw vertical lines
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

    # Section labels
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
        (width // 2 - 60, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        "RIGHT",
        (width - 110, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    # Show output
    cv2.imshow(
        "Smart Vision - Position Detection",
        annotated_frame
    )

    # Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()