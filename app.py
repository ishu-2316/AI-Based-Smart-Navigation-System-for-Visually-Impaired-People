from flask import Flask, Response, jsonify, render_template_string
import cv2
import time
import threading
import queue
import pyttsx3
import pythoncom
from ultralytics import YOLO

app = Flask(__name__)

MODEL_PATH = "yolo11n.pt"
CONFIDENCE = 0.40
ANNOUNCE_INTERVAL = 3.0
REPEAT_COUNT = 3

model = YOLO(MODEL_PATH)

camera = None
camera_lock = threading.Lock()
running = False
voice_enabled = True

latest_frame = None
latest_status = {
    "objects": [],
    "fps": 0,
    "camera": False,
    "voice": True,
    "message": "System ready"
}

voice_queue = queue.Queue(maxsize=1)
stop_voice = threading.Event()
last_announced = {}


def friendly_name(name):
    return {
        "cell phone": "phone",
        "motorcycle": "bike",
        "bicycle": "bicycle",
        "backpack": "bag",
        "handbag": "bag",
        "dining table": "table",
        "tv": "television",
    }.get(name, name)


def get_position(cx, width):
    if cx < width / 3:
        return "left"
    if cx > width * 2 / 3:
        return "right"
    return "ahead"


def make_message(name, position):
    return f"{name} on your {position}" if position != "ahead" else f"{name} ahead"


def speak(message):
    if not voice_enabled:
        return
    try:
        while True:
            voice_queue.get_nowait()
            voice_queue.task_done()
    except queue.Empty:
        pass
    try:
        voice_queue.put_nowait(message)
    except queue.Full:
        pass


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

        latest_status["message"] = message
        for _ in range(REPEAT_COUNT):
            if stop_voice.is_set():
                break
            engine.say(message)
        engine.runAndWait()
        voice_queue.task_done()

    engine.stop()
    pythoncom.CoUninitialize()


threading.Thread(target=voice_worker, daemon=True).start()


def camera_loop():
    global camera, running, latest_frame

    with camera_lock:
        if camera is None:
            camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not camera.isOpened():
                camera.release()
                camera = None
                running = False
                latest_status["message"] = "Camera could not be opened"
                return

    prev = time.time()
    frame_count = 0
    fps = 0

    while running:
        ok, frame = camera.read()
        if not ok:
            time.sleep(0.05)
            continue

        h, w = frame.shape[:2]
        left_line = w // 3
        right_line = (w * 2) // 3

        cv2.line(frame, (left_line, 0), (left_line, h), (255,255,255), 2)
        cv2.line(frame, (right_line, 0), (right_line, h), (255,255,255), 2)

        results = model(frame, conf=CONFIDENCE, verbose=False)
        objects = []
        current_keys = set()
        now = time.time()

        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < CONFIDENCE:
                    continue

                cls_id = int(box.cls[0])
                raw = model.names[cls_id]
                name = friendly_name(raw)

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                position = get_position(cx, w)

                key = f"{name}|{position}"
                current_keys.add(key)

                objects.append({
                    "name": name,
                    "position": position,
                    "confidence": round(conf * 100),
                })

                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,220,255), 2)
                cv2.circle(frame, (cx,cy), 5, (0,220,255), -1)
                cv2.putText(
                    frame,
                    f"{name} {conf:.2f} [{position}]",
                    (x1, max(22, y1-8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255,255,255),
                    2
                )

                if key not in last_announced or now - last_announced[key] >= ANNOUNCE_INTERVAL:
                    message = make_message(name, position)
                    speak(message)
                    last_announced[key] = now

        # Forget objects that have disappeared, so they announce when they return.
        for key in list(last_announced.keys()):
            if key not in current_keys and now - last_announced[key] > 2:
                del last_announced[key]

        # Dashboard labels
        cv2.putText(frame, "LEFT", (25, 40), cv2.FONT_HERSHEY_SIMPLEX, .75, (255,255,255), 2)
        cv2.putText(frame, "CENTER", (left_line+20, 40), cv2.FONT_HERSHEY_SIMPLEX, .75, (255,255,255), 2)
        cv2.putText(frame, "RIGHT", (right_line+20, 40), cv2.FONT_HERSHEY_SIMPLEX, .75, (255,255,255), 2)

        frame_count += 1
        elapsed = time.time() - prev
        if elapsed >= 1:
            fps = frame_count / elapsed
            frame_count = 0
            prev = time.time()

        cv2.putText(frame, f"SMART VISION ACTIVE | FPS {fps:.1f}",
                    (18, h-18), cv2.FONT_HERSHEY_SIMPLEX, .65, (0,255,170), 2)

        latest_status["objects"] = objects
        latest_status["fps"] = round(fps, 1)
        latest_status["camera"] = True
        latest_status["voice"] = voice_enabled

        ok2, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if ok2:
            latest_frame = jpg.tobytes()

    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None
    latest_status["camera"] = False


def start_camera():
    global running
    if running:
        return
    running = True
    threading.Thread(target=camera_loop, daemon=True).start()


def stop_camera():
    global running
    running = False
    latest_status["camera"] = False


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/start")
def start():
    start_camera()
    return jsonify(ok=True)


@app.route("/stop")
def stop():
    stop_camera()
    return jsonify(ok=True)


@app.route("/voice")
def toggle_voice():
    global voice_enabled
    voice_enabled = not voice_enabled
    latest_status["voice"] = voice_enabled
    return jsonify(voice=voice_enabled)


@app.route("/read")
def read_scene():
    if latest_status["objects"]:
        parts = []
        for o in latest_status["objects"][:5]:
            parts.append(make_message(o["name"], o["position"]))
        speak(". ".join(parts))
        latest_status["message"] = ". ".join(parts)
    else:
        speak("No objects detected")
        latest_status["message"] = "No objects detected"
    return jsonify(ok=True)


@app.route("/status")
def status():
    latest_status["voice"] = voice_enabled
    latest_status["camera"] = running
    return jsonify(latest_status)


@app.route("/video")
def video():
    def generate():
        while True:
            if latest_frame is not None:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" +
                       latest_frame + b"\r\n")
            time.sleep(0.04)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


PAGE = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Smart Navigation</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#07101f;color:#eef5ff;font-family:Segoe UI,Arial,sans-serif}
header{padding:24px 32px;border-bottom:1px solid #263652;background:#101a2e}
.badge{display:inline-block;background:#10bfe5;color:#06101d;padding:7px 13px;border-radius:7px;font-weight:800;font-size:12px;letter-spacing:.7px}
h1{margin:12px 0 4px;font-size:30px}header p{margin:0;color:#a9c3e8;font-size:16px}
.status{float:right;margin-top:-45px;background:#0b3d32;border:1px solid #12bd85;padding:11px 18px;border-radius:28px;color:#51e3ae;font-weight:700}
main{padding:24px 32px}.controls{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
button{border:0;border-radius:9px;padding:18px;font-size:17px;font-weight:800;color:white;cursor:pointer;background:#2456df}
button.stop{background:#53627b}button.voice{background:#087fb4}button.read{background:#08a36f}
.grid{display:grid;grid-template-columns:1.65fr 1fr;gap:24px}
.card{background:#101a2e;border:1px solid #304261;border-radius:16px;overflow:hidden;box-shadow:0 8px 25px #0003}
.card h2{font-size:20px;margin:0;padding:22px;border-bottom:1px solid #293b58}
.video{background:#02050a;min-height:480px;display:flex;align-items:center;justify-content:center}
.video img{width:100%;display:block}.empty{color:#7590b6}
.side{display:flex;flex-direction:column;gap:24px}.objects{padding:18px}.obj{padding:13px 0;border-bottom:1px solid #263650;display:flex;justify-content:space-between}
.obj strong{font-size:16px}.pos{color:#55d9ff}.conf{color:#8ee7b9}
.panel{padding:20px}.row{display:flex;justify-content:space-between;margin:13px 0;color:#b7cae5}
.big{font-size:20px;color:#58dfb0;font-weight:800}.voicebox{background:#0a1425;border:1px solid #2c4160;border-radius:12px;padding:18px;margin:15px 20px;color:#8edfff}
.footer{padding:20px 32px;color:#7086a5;font-size:13px}
@media(max-width:900px){.controls,.grid{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}.status{float:none;margin:15px 0 0}}
</style>
</head>
<body>
<header>
<div class="badge">ASSISTIVE AI VISION</div>
<div class="status" id="system">● SYSTEM READY</div>
<h1>AI-Based Smart Navigation System</h1>
<p>Real-time Computer Vision & Continuous Spatial Voice Guidance for Visually Impaired People</p>
</header>
<main>
<div class="controls">
<button onclick="start()">▶ START CAMERA</button>
<button class="stop" onclick="stop()">■ STOP CAMERA</button>
<button class="voice" onclick="toggleVoice()" id="voiceBtn">🔊 VOICE: ON</button>
<button class="read" onclick="readScene()">🔎 READ SCENE</button>
</div>

<div class="grid">
<section class="card">
<h2>Live Camera Stream <span style="float:right;font-size:13px;color:#63e0b0" id="fps">FPS: --</span></h2>
<div class="video" id="videoBox"><div class="empty">Press START CAMERA</div></div>
</section>

<aside class="side">
<section class="card">
<h2>Detected Objects <span style="float:right;color:#18c9e9" id="count">0</span></h2>
<div class="objects" id="objects"><div class="empty">No objects detected.</div></div>
</section>

<section class="card">
<h2>AI Engine Status</h2>
<div class="panel">
<div class="row">Camera <span class="big" id="cam">OFFLINE</span></div>
<div class="row">Voice <span class="big" id="voice">ON</span></div>
<div class="row">YOLO Confidence <span>40%</span></div>
<div class="row">Voice Repeat <span>3×</span></div>
<div class="row">Repeat Interval <span>3 sec</span></div>
</div>
<div class="voicebox">🔊 <b>Last Guidance</b><br><span id="msg">System ready</span></div>
</section>
</aside>
</div>
</main>
<div class="footer">AI-Based Smart Navigation System • Computer Vision & Image Analysis • YOLO + OpenCV + Python TTS</div>

<script>
async function start(){
 await fetch('/start');
 document.getElementById('videoBox').innerHTML='<img src="/video" alt="Live camera">';
}
async function stop(){await fetch('/stop');location.reload()}
async function toggleVoice(){
 let r=await fetch('/voice');let d=await r.json();
 document.getElementById('voiceBtn').innerText=d.voice?'🔊 VOICE: ON':'🔇 VOICE: OFF';
}
async function readScene(){await fetch('/read')}
async function update(){
 try{
  let r=await fetch('/status');let d=await r.json();
  document.getElementById('fps').innerText='FPS: '+d.fps;
  document.getElementById('cam').innerText=d.camera?'ONLINE':'OFFLINE';
  document.getElementById('voice').innerText=d.voice?'ON':'OFF';
  document.getElementById('voiceBtn').innerText=d.voice?'🔊 VOICE: ON':'🔇 VOICE: OFF';
  document.getElementById('system').innerText=d.camera?'● SYSTEM ACTIVE':'● SYSTEM READY';
  document.getElementById('msg').innerText=d.message;
  document.getElementById('count').innerText=d.objects.length;
  let box=document.getElementById('objects');
  if(!d.objects.length){box.innerHTML='<div class="empty">No objects detected.</div>'}
  else{
   box.innerHTML=d.objects.map(o=>`<div class="obj"><strong>${o.name.toUpperCase()}</strong><span class="pos">${o.position.toUpperCase()}</span><span class="conf">${o.confidence}%</span></div>`).join('');
  }
 }catch(e){}
}
setInterval(update,700);update();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("Starting Professional Smart Navigation Dashboard...")
    print("Open: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
