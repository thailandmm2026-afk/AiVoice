# -*- coding: utf-8 -*-
"""
Movie Recap TTS Web App
Backend: Flask + edge-tts
Frontend: Modern Myanmar UI (works in all browsers)
"""

import os
import asyncio
import io
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_file, Response

import edge_tts

# =========================================================
# CONFIG
# =========================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

VOICES = {
    "thiha": {
        "id": "my-MM-ThihaNeural",
        "name": "Thiha",
        "gender": "ကျား"
    },
    "nilar": {
        "id": "my-MM-NilarNeural",
        "name": "Nilar",
        "gender": "မ"
    }
}

DEFAULT_VOICE = "thiha"
DEFAULT_SPEED = 1.4
SPEED_OPTIONS = [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]

VOICE_VOLUME = "+0%"
VOICE_PITCH = "+0Hz"


def speed_to_edge_rate(speed: float) -> str:
    percentage = round((speed - 1.0) * 100)
    if percentage >= 0:
        return f"+{percentage}%"
    return f"{percentage}%"


async def generate_audio(text: str, voice_key: str, speed: float) -> bytes:
    rate = speed_to_edge_rate(speed)
    voice_id = VOICES[voice_key]["id"]

    logger.info(f"TTS | Voice={voice_key} | Speed={speed}x | Rate={rate}")

    communicate = edge_tts.Communicate(
        text,
        voice_id,
        rate=rate,
        volume=VOICE_VOLUME,
        pitch=VOICE_PITCH
    )

    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])

    audio_buffer.seek(0)
    return audio_buffer.read()


# =========================================================
# API ROUTES
# =========================================================

@app.route("/api/tts", methods=["POST"])
def api_tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice_key = data.get("voice", DEFAULT_VOICE)
    speed = float(data.get("speed", DEFAULT_SPEED))

    if not text:
        return jsonify({"error": "စာသား မရှိပါ"}), 400

    if voice_key not in VOICES:
        return jsonify({"error": "အသံ မမှန်ကန်ပါ"}), 400

    if speed not in SPEED_OPTIONS:
        # allow closest or clamp
        speed = min(SPEED_OPTIONS, key=lambda x: abs(x - speed))

    try:
        audio_bytes = asyncio.run(generate_audio(text, voice_key, speed))

        if not audio_bytes:
            return jsonify({"error": "အသံဖိုင် ထုတ်မရပါ"}), 500

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Movie_Recap_{voice_key}_{speed:.1f}x_{timestamp}.mp3"

        return send_file(
            io.BytesIO(audio_bytes),
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name=filename
        )

    except Exception as e:
        logger.exception("TTS Error")
        return jsonify({"error": str(e)}), 500


@app.route("/api/voices", methods=["GET"])
def api_voices():
    return jsonify({
        "voices": VOICES,
        "speeds": SPEED_OPTIONS,
        "default_voice": DEFAULT_VOICE,
        "default_speed": DEFAULT_SPEED
    })


# =========================================================
# FRONTEND (Single Page)
# =========================================================

HTML_PAGE = r'''<!DOCTYPE html>
<html lang="my">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>🎬 Movie Recap TTS - Myanmar AI Voice</title>
  <style>
    :root {
      --bg: #0f0f13;
      --card: #1a1a24;
      --card-hover: #22222e;
      --primary: #7c5cff;
      --primary-hover: #6a4de0;
      --accent: #ff6b9d;
      --text: #f0f0f5;
      --text-muted: #a0a0b0;
      --border: #2a2a3a;
      --success: #2dd4a8;
      --danger: #ff5c7a;
      --radius: 16px;
      --shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', 'Pyidaungsu', 'Noto Sans Myanmar', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      line-height: 1.6;
      background-image:
        radial-gradient(ellipse at 20% 20%, rgba(124, 92, 255, 0.15) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 80%, rgba(255, 107, 157, 0.1) 0%, transparent 50%);
    }
    .container { max-width: 720px; margin: 0 auto; padding: 24px 16px 60px; }
    header { text-align: center; margin-bottom: 32px; padding-top: 20px; }
    header h1 {
      font-size: 1.9rem; font-weight: 700;
      background: linear-gradient(135deg, #7c5cff, #ff6b9d);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
      margin-bottom: 8px;
    }
    header p { color: var(--text-muted); font-size: 0.95rem; }
    .card {
      background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
      padding: 24px; margin-bottom: 20px; box-shadow: var(--shadow); transition: background 0.2s;
    }
    .card:hover { background: var(--card-hover); }
    .card-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
    .voice-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .voice-btn, .speed-btn {
      background: var(--bg); border: 2px solid var(--border); border-radius: 12px;
      padding: 14px 12px; color: var(--text); font-size: 0.95rem; cursor: pointer;
      transition: all 0.2s; text-align: center; font-family: inherit;
    }
    .voice-btn:hover, .speed-btn:hover { border-color: var(--primary); background: rgba(124, 92, 255, 0.1); }
    .voice-btn.active, .speed-btn.active {
      border-color: var(--primary); background: rgba(124, 92, 255, 0.2); box-shadow: 0 0 0 1px var(--primary);
    }
    .voice-btn .gender { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }
    .speed-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    @media (max-width: 480px) { .speed-grid { grid-template-columns: repeat(3, 1fr); } }
    textarea {
      width: 100%; min-height: 180px; background: var(--bg); border: 2px solid var(--border);
      border-radius: 12px; padding: 16px; color: var(--text); font-size: 1rem; font-family: inherit;
      resize: vertical; transition: border-color 0.2s; line-height: 1.7;
    }
    textarea:focus { outline: none; border-color: var(--primary); }
    textarea::placeholder { color: var(--text-muted); }
    .char-count { text-align: right; font-size: 0.8rem; color: var(--text-muted); margin-top: 8px; }
    .btn-row { display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap; }
    .btn {
      flex: 1; min-width: 140px; padding: 14px 20px; border: none; border-radius: 12px;
      font-size: 1rem; font-weight: 600; cursor: pointer; font-family: inherit;
      transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px;
    }
    .btn-primary { background: linear-gradient(135deg, #7c5cff, #9b6dff); color: white; }
    .btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(124, 92, 255, 0.4); }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    .btn-secondary { background: var(--bg); color: var(--text); border: 2px solid var(--border); }
    .btn-secondary:hover:not(:disabled) { border-color: var(--primary); }
    .status {
      margin-top: 16px; padding: 14px 16px; border-radius: 12px; font-size: 0.95rem;
      display: none; align-items: center; gap: 10px;
    }
    .status.show { display: flex; }
    .status.loading { background: rgba(124, 92, 255, 0.15); border: 1px solid rgba(124, 92, 255, 0.3); color: #c4b5ff; }
    .status.success { background: rgba(45, 212, 168, 0.15); border: 1px solid rgba(45, 212, 168, 0.3); color: var(--success); }
    .status.error { background: rgba(255, 92, 122, 0.15); border: 1px solid rgba(255, 92, 122, 0.3); color: var(--danger); }
    .spinner {
      width: 18px; height: 18px; border: 2px solid transparent; border-top-color: currentColor;
      border-radius: 50%; animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .audio-player { margin-top: 20px; display: none; }
    .audio-player.show { display: block; }
    audio { width: 100%; border-radius: 12px; margin-bottom: 12px; }
    .download-row { display: flex; gap: 10px; flex-wrap: wrap; }
    .download-btn {
      flex: 1; min-width: 140px; padding: 12px; background: var(--bg); border: 2px solid var(--border);
      border-radius: 10px; color: var(--text); font-size: 0.9rem; cursor: pointer; font-family: inherit;
      transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 6px;
    }
    .download-btn:hover { border-color: var(--success); background: rgba(45, 212, 168, 0.1); }
    .info-box {
      background: rgba(124, 92, 255, 0.08); border: 1px solid rgba(124, 92, 255, 0.2);
      border-radius: 12px; padding: 16px; font-size: 0.9rem; color: var(--text-muted); line-height: 1.7;
    }
    .info-box strong { color: var(--text); }
    footer { text-align: center; margin-top: 40px; color: var(--text-muted); font-size: 0.85rem; }
    .current-settings {
      display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 8px;
      font-size: 0.9rem; color: var(--text-muted);
    }
    .current-settings span {
      background: var(--card); padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border);
    }
    .current-settings strong { color: var(--primary); }
    .badge {
      display: inline-block; background: rgba(45, 212, 168, 0.2); color: var(--success);
      font-size: 0.75rem; padding: 2px 8px; border-radius: 6px; margin-left: 8px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>🎬 Movie Recap TTS</h1>
      <p>မြန်မာ AI အသံဖြင့် စာသားကို အသံဖိုင်အဖြစ် ပြောင်းပါ <span class="badge">Backend</span></p>
      <div class="current-settings" id="currentSettings">
        <span>🎤 <strong id="displayVoice">Thiha (ကျား)</strong></span>
        <span>⚡ <strong id="displaySpeed">1.4x</strong></span>
      </div>
    </header>

    <div class="card">
      <div class="card-title">🎤 အသံရွေးပါ</div>
      <div class="voice-grid">
        <button class="voice-btn active" data-voice="thiha" onclick="selectVoice('thiha')">
          <div>Thiha</div>
          <div class="gender">ကျားအသံ</div>
        </button>
        <button class="voice-btn" data-voice="nilar" onclick="selectVoice('nilar')">
          <div>Nilar</div>
          <div class="gender">မအသံ</div>
        </button>
      </div>
    </div>

    <div class="card">
      <div class="card-title">⚡ အသံအမြန်နှုန်း</div>
      <div class="speed-grid" id="speedGrid"></div>
      <p style="margin-top:12px;font-size:0.85rem;color:var(--text-muted);">
        🎬 Movie Recap အတွက် အကြံပြုချက်: <strong style="color:var(--primary)">1.4x</strong>
      </p>
    </div>

    <div class="card">
      <div class="card-title">📝 စာသားထည့်ပါ</div>
      <textarea id="textInput" placeholder="အသံပြောင်းလိုသော မြန်မာစာသားကို ဤနေရာတွင် ရိုက်ထည့်ပါ...&#10;&#10;ပုဒ်ဖြတ်ပုဒ်ရပ် (၊ ။) တွေ ထည့်ပေးရင် အသံထွက်ပိုကောင်းပါတယ်။"></textarea>
      <div class="char-count"><span id="charCount">0</span> စာလုံး</div>

      <div class="btn-row">
        <button class="btn btn-primary" id="generateBtn" onclick="generateTTS()">
          🎙 အသံဖိုင် ဖန်တီးမည်
        </button>
        <button class="btn btn-secondary" onclick="clearText()">🗑 ရှင်းမည်</button>
      </div>

      <div class="status" id="statusBox"></div>

      <div class="audio-player" id="audioPlayer">
        <audio id="audioElement" controls></audio>
        <div class="download-row">
          <button class="download-btn" onclick="downloadAudio()">🎧 MP3 ဒေါင်းလုပ်</button>
          <button class="download-btn" onclick="downloadTranscript()">📝 Transcript TXT</button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="info-box">
        <strong>📌 အသုံးပြုပုံ</strong><br>
        ၁။ အသံ (Thiha / Nilar) နှင့် အမြန်နှုန်း ရွေးပါ<br>
        ၂။ စာသား ရိုက်ထည့်ပါ<br>
        ၃။ 「အသံဖိုင် ဖန်တီးမည်」 ကို နှိပ်ပါ<br>
        ၄။ MP3 နှင့် Transcript ကို ဒေါင်းလုပ်ယူပါ<br><br>
        <strong>✅ Backend version</strong> — Chrome, Firefox, Safari, Edge အားလုံးမှာ အလုပ်လုပ်ပါတယ်။
      </div>
    </div>

    <footer>
      Movie Recap TTS Web • Powered by Microsoft Edge Neural Voices<br>
      Thiha & Nilar Myanmar AI Voices
    </footer>
  </div>

  <script>
    const VOICES = {
      thiha: { id: "my-MM-ThihaNeural", name: "Thiha", gender: "ကျား" },
      nilar: { id: "my-MM-NilarNeural", name: "Nilar", gender: "မ" }
    };
    const SPEED_OPTIONS = [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0];
    const DEFAULT_VOICE = "thiha";
    const DEFAULT_SPEED = 1.4;

    let currentVoice = localStorage.getItem("tts_voice") || DEFAULT_VOICE;
    let currentSpeed = parseFloat(localStorage.getItem("tts_speed")) || DEFAULT_SPEED;
    let lastAudioBlob = null;
    let lastText = "";
    let lastFilename = "";

    function init() {
      const speedGrid = document.getElementById("speedGrid");
      SPEED_OPTIONS.forEach(speed => {
        const btn = document.createElement("button");
        btn.className = "speed-btn" + (speed === currentSpeed ? " active" : "");
        btn.textContent = speed.toFixed(1) + "x";
        btn.dataset.speed = speed;
        btn.onclick = () => selectSpeed(speed);
        speedGrid.appendChild(btn);
      });
      document.querySelectorAll(".voice-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.voice === currentVoice);
      });
      updateDisplay();
      document.getElementById("textInput").addEventListener("input", e => {
        document.getElementById("charCount").textContent = e.target.value.length;
      });
    }

    function updateDisplay() {
      const v = VOICES[currentVoice];
      document.getElementById("displayVoice").textContent = `${v.name} (${v.gender})`;
      document.getElementById("displaySpeed").textContent = currentSpeed.toFixed(1) + "x";
    }

    function selectVoice(key) {
      currentVoice = key;
      localStorage.setItem("tts_voice", key);
      document.querySelectorAll(".voice-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.voice === key);
      });
      updateDisplay();
    }

    function selectSpeed(speed) {
      currentSpeed = speed;
      localStorage.setItem("tts_speed", speed);
      document.querySelectorAll(".speed-btn").forEach(btn => {
        btn.classList.toggle("active", parseFloat(btn.dataset.speed) === speed);
      });
      updateDisplay();
    }

    function clearText() {
      document.getElementById("textInput").value = "";
      document.getElementById("charCount").textContent = "0";
      document.getElementById("audioPlayer").classList.remove("show");
      hideStatus();
    }

    function showStatus(type, message) {
      const box = document.getElementById("statusBox");
      box.className = "status show " + type;
      box.innerHTML = type === "loading" ? `<div class="spinner"></div> ${message}` : message;
    }

    function hideStatus() {
      document.getElementById("statusBox").className = "status";
    }

    async function generateTTS() {
      const text = document.getElementById("textInput").value.trim();
      if (!text) {
        showStatus("error", "⚠️ ကျေးဇူးပြု၍ အသံပြောင်းလိုသော စာသားကို ပို့ပေးပါ။");
        return;
      }

      const btn = document.getElementById("generateBtn");
      btn.disabled = true;
      const voice = VOICES[currentVoice];
      showStatus("loading", `${voice.name} အသံဖြင့် ${currentSpeed.toFixed(1)}x အမြန်နှုန်းဖြင့် အသံဖိုင်ဖန်တီးနေပါသည်...`);

      try {
        const res = await fetch("/api/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: text,
            voice: currentVoice,
            speed: currentSpeed
          })
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || "Server error");
        }

        const blob = await res.blob();
        lastAudioBlob = blob;
        lastText = text;
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
        lastFilename = `Movie_Recap_${currentVoice}_${currentSpeed.toFixed(1)}x_${timestamp}`;

        const url = URL.createObjectURL(blob);
        const audioEl = document.getElementById("audioElement");
        audioEl.src = url;
        document.getElementById("audioPlayer").classList.add("show");

        showStatus("success", `✅ အသံဖိုင် အဆင်သင့်ဖြစ်ပါပြီ! (${voice.name} • ${currentSpeed.toFixed(1)}x)`);
      } catch (err) {
        console.error(err);
        showStatus("error", "❌ အသံဖိုင်ပြောင်းလဲရာတွင် အမှားအယွင်းရှိနေပါသည်။<br>ခဏနားပြီး ပြန်စမ်းကြည့်ပါ။");
      } finally {
        btn.disabled = false;
      }
    }

    function downloadAudio() {
      if (!lastAudioBlob) return;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(lastAudioBlob);
      a.download = lastFilename + ".mp3";
      a.click();
    }

    function downloadTranscript() {
      if (!lastText) return;
      const voice = VOICES[currentVoice];
      const content = `🎬 Movie Recap TTS Transcript
================================

🎤 Voice: ${voice.name} (${voice.gender})
⚡ Speed: ${currentSpeed.toFixed(1)}x
📅 Created: ${new Date().toLocaleString()}

================================

${lastText}

================================
Generated by Movie Recap TTS Web`;
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `Transcript_${lastFilename}.txt`;
      a.click();
    }

    init();
  </script>
</body>
</html>
'''


@app.route("/")
def index():
    return Response(HTML_PAGE, mimetype="text/html")


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Movie Recap TTS Web starting...")
    logger.info(f"Default Voice: {DEFAULT_VOICE} | Default Speed: {DEFAULT_SPEED}x")
    logger.info(f"Open http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
