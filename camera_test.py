import cv2

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera open avvaledu!")
    exit()

print("Camera started successfully!")
print("Q press chesthe camera close avutundi.")

while True:
    success, frame = camera.read()

    if not success:
        print("Camera frame read avvaledu!")
        break

    cv2.imshow("Smart Vision - Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()