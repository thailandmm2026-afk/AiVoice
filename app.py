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
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#070812">
<title>Movie Recap AI Studio</title>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Myanmar:wght@400;500;600;700&display=swap');

:root {
  --bg: #05060b;
  --bg2: #080a13;
  --panel: rgba(14, 16, 28, .82);
  --panel2: rgba(20, 22, 38, .72);
  --line: rgba(255,255,255,.09);

  --purple: #8b5cf6;
  --violet: #a855f7;
  --cyan: #22d3ee;
  --pink: #ec4899;
  --green: #34d399;

  --text: #f7f7fb;
  --muted: #8f94a8;

  --radius: 24px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  width: 100%;
  min-height: 100%;
  overflow-x: hidden;
  scroll-behavior: smooth;
}

body {
  width: 100%;
  min-width: 0;
  min-height: 100vh;
  overflow-x: hidden;

  color: var(--text);
  font-family: Inter, "Noto Sans Myanmar", "Segoe UI", sans-serif;

  background:
    radial-gradient(circle at 15% 10%, rgba(139,92,246,.18), transparent 30%),
    radial-gradient(circle at 85% 25%, rgba(34,211,238,.10), transparent 28%),
    radial-gradient(circle at 60% 90%, rgba(236,72,153,.10), transparent 32%),
    #05060b;
}

/* ================================
   BACKGROUND
================================ */

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: .22;
  background-image:
    linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(to bottom, black, transparent 90%);
}

body::after {
  content: "";
  position: fixed;
  width: 420px;
  height: 420px;
  left: -220px;
  top: 35%;
  border-radius: 50%;
  background: rgba(139,92,246,.10);
  filter: blur(100px);
  pointer-events: none;
}

/* ================================
   APP
================================ */

.app {
  width: min(980px, calc(100% - 28px));
  margin: auto;
  padding: 22px 0 70px;
}

/* ================================
   TOP NAV
================================ */

.topbar {
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
  padding: 0 20px;

  background: rgba(10,11,20,.68);
  border: 1px solid var(--line);
  border-radius: 20px;
  backdrop-filter: blur(20px);
  box-shadow: 0 20px 60px rgba(0,0,0,.25);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  width: 42px;
  height: 42px;
  border-radius: 13px;

  display: grid;
  place-items: center;

  font-size: 20px;

  background:
    linear-gradient(135deg, rgba(139,92,246,.35), rgba(34,211,238,.15));

  border: 1px solid rgba(139,92,246,.45);

  box-shadow:
    0 0 25px rgba(139,92,246,.25),
    inset 0 0 20px rgba(139,92,246,.12);
}

.brand-text strong {
  display: block;
  font-size: 14px;
  letter-spacing: .4px;
}

.brand-text span {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  font-size: 10px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
}

.live {
  display: flex;
  align-items: center;
  gap: 7px;

  padding: 8px 12px;
  border-radius: 30px;

  background: rgba(52,211,153,.07);
  border: 1px solid rgba(52,211,153,.18);

  color: #70e8bb;
  font-size: 11px;
  font-weight: 600;
}

.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 12px var(--green);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  50% { opacity: .35; transform: scale(.7); }
}

/* ================================
   HERO
================================ */

.hero {
  position: relative;
  overflow: hidden;

  min-height: 280px;
  padding: 42px 34px;

  border-radius: 30px;
  border: 1px solid rgba(139,92,246,.22);

  background:
    radial-gradient(circle at 75% 20%, rgba(34,211,238,.13), transparent 30%),
    radial-gradient(circle at 15% 100%, rgba(139,92,246,.18), transparent 40%),
    linear-gradient(135deg, rgba(18,18,32,.96), rgba(8,9,16,.92));

  box-shadow:
    0 30px 90px rgba(0,0,0,.45),
    inset 0 1px rgba(255,255,255,.04);
}

.hero::before {
  content: "";
  position: absolute;
  width: 300px;
  height: 300px;
  right: -100px;
  top: -130px;
  border-radius: 50%;
  border: 1px solid rgba(34,211,238,.15);
  box-shadow:
    0 0 60px rgba(34,211,238,.08),
    inset 0 0 50px rgba(34,211,238,.05);
}

.hero::after {
  content: "";
  position: absolute;
  width: 160px;
  height: 160px;
  right: 30px;
  bottom: -80px;
  border-radius: 50%;
  background: rgba(236,72,153,.12);
  filter: blur(60px);
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 650px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  padding: 7px 12px;
  margin-bottom: 18px;

  border-radius: 30px;
  background: rgba(139,92,246,.10);
  border: 1px solid rgba(139,92,246,.22);

  color: #bda9ff;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}

.hero h1 {
  font-size: clamp(32px, 7vw, 58px);
  line-height: 1.02;
  letter-spacing: -2px;
  font-weight: 800;

  background: linear-gradient(
    100deg,
    #fff 10%,
    #c9b8ff 48%,
    #65e9ff 100%
  );

  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero p {
  max-width: 560px;
  margin-top: 17px;

  color: #9b9fb3;
  font-size: 14px;
  line-height: 1.9;
}

.hero-orb {
  position: absolute;
  right: 70px;
  top: 75px;

  width: 100px;
  height: 100px;
  border-radius: 50%;

  border: 1px solid rgba(139,92,246,.55);

  box-shadow:
    0 0 20px rgba(139,92,246,.35),
    0 0 70px rgba(139,92,246,.18),
    inset 0 0 30px rgba(34,211,238,.18);

  animation: floatOrb 4s ease-in-out infinite;
}

.hero-orb::before,
.hero-orb::after {
  content: "";
  position: absolute;
  inset: 13px;
  border-radius: 50%;
  border: 1px solid rgba(34,211,238,.35);
}

.hero-orb::after {
  inset: 29px;
  border-color: rgba(236,72,153,.45);
}

@keyframes floatOrb {
  50% {
    transform: translateY(-12px) rotate(12deg);
  }
}

/* ================================
   GRID
================================ */

.workspace {
  width: 100%;
  min-width: 0;

  display: grid;

  grid-template-columns:
    minmax(0, 1fr)
    minmax(0, 1fr);

  gap: 18px;
  margin-top: 18px;
}

.panel {
  position: relative;

  width: 100%;
  min-width: 0;

  overflow: hidden;

  background: var(--panel);

  border: 1px solid var(--line);
  border-radius: var(--radius);

  padding: 22px;

  backdrop-filter: blur(20px);

  box-shadow:
    0 20px 70px rgba(0,0,0,.30),
    inset 0 1px rgba(255,255,255,.025);
}

.panel.full {
  grid-column: 1 / -1;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;

  margin-bottom: 18px;
}

.panel-title-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-icon {
  width: 34px;
  height: 34px;

  display: grid;
  place-items: center;

  border-radius: 10px;
  background: rgba(139,92,246,.10);
  border: 1px solid rgba(139,92,246,.18);

  font-size: 16px;
}

.panel-title strong {
  font-size: 14px;
}

.panel-title small {
  color: var(--muted);
  font-size: 10px;
}

/* ================================
   VOICE CARDS
================================ */

.voice-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.voice-card {
  position: relative;
  overflow: hidden;

  padding: 18px 15px;

  background: rgba(5,6,12,.65);
  border: 1px solid var(--line);
  border-radius: 18px;

  color: white;
  cursor: pointer;
  text-align: left;

  transition: .25s;
}

.voice-card:hover {
  transform: translateY(-2px);
  border-color: rgba(139,92,246,.5);
}

.voice-card.active {
  border-color: rgba(139,92,246,.8);

  background:
    radial-gradient(circle at 20% 20%, rgba(139,92,246,.20), transparent 55%),
    rgba(12,10,24,.9);

  box-shadow:
    0 0 0 1px rgba(139,92,246,.16),
    0 0 35px rgba(139,92,246,.12);
}

.voice-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.voice-avatar {
  width: 42px;
  height: 42px;

  display: grid;
  place-items: center;

  border-radius: 13px;

  font-size: 19px;

  background:
    linear-gradient(135deg, rgba(139,92,246,.3), rgba(34,211,238,.08));

  border: 1px solid rgba(139,92,246,.35);
}

.voice-card:nth-child(2) .voice-avatar {
  background:
    linear-gradient(135deg, rgba(236,72,153,.28), rgba(139,92,246,.08));

  border-color: rgba(236,72,153,.35);
}

.check {
  width: 21px;
  height: 21px;

  display: grid;
  place-items: center;

  border-radius: 50%;
  border: 1px solid #383b4c;

  color: transparent;
  font-size: 11px;
}

.voice-card.active .check {
  color: white;
  background: var(--purple);
  border-color: var(--purple);
  box-shadow: 0 0 15px rgba(139,92,246,.55);
}

.voice-name {
  margin-top: 13px;
  font-size: 14px;
  font-weight: 700;
}

.voice-gender {
  margin-top: 3px;
  color: var(--muted);
  font-size: 11px;
}

/* ================================
   SPEED
================================ */

.speed-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.speed {
  padding: 11px 5px;

  border: 1px solid var(--line);
  border-radius: 12px;

  background: rgba(5,6,12,.65);
  color: #aaaebe;

  cursor: pointer;
  font-weight: 600;
  font-size: 12px;

  transition: .2s;
}

.speed:hover {
  border-color: rgba(34,211,238,.4);
  color: white;
}

.speed.active {
  color: white;

  background:
    linear-gradient(135deg, rgba(139,92,246,.25), rgba(34,211,238,.08));

  border-color: rgba(139,92,246,.65);

  box-shadow: 0 0 20px rgba(139,92,246,.10);
}

.speed-recommend {
  margin-top: 13px;
  color: var(--muted);
  font-size: 10px;
}

.speed-recommend b {
  color: var(--cyan);
}

/* ================================
   TEXT EDITOR
================================ */

.editor {
  position: relative;
}

.textarea-wrap {
  position: relative;
}

textarea {
  width: 100%;
  min-height: 230px;

  resize: vertical;

  padding: 19px;

  color: #f4f4f8;

  font-family: inherit;
  font-size: 14px;
  line-height: 1.9;

  background:
    radial-gradient(circle at 90% 10%, rgba(139,92,246,.06), transparent 30%),
    rgba(4,5,10,.72);

  border: 1px solid var(--line);
  border-radius: 18px;

  outline: none;

  transition: .25s;
}

textarea:focus {
  border-color: rgba(139,92,246,.65);

  box-shadow:
    0 0 0 3px rgba(139,92,246,.07),
    0 0 40px rgba(139,92,246,.08);
}

textarea::placeholder {
  color: #5f6375;
}

.editor-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;

  margin-top: 10px;
}

.char-count {
  color: #65697b;
  font-size: 10px;
}

.tip {
  color: #737789;
  font-size: 10px;
}

/* ================================
   GENERATE BUTTON
================================ */

.generate {
  position: relative;
  overflow: hidden;

  width: 100%;
  height: 58px;

  margin-top: 17px;

  border: 0;
  border-radius: 17px;

  color: white;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;

  cursor: pointer;

  background:
    linear-gradient(110deg,
      #6d42df,
      #974ee9,
      #4777ff,
      #16a8c5
    );

  background-size: 250% 100%;

  box-shadow:
    0 12px 35px rgba(124,92,246,.22);

  animation: gradientMove 5s ease infinite;

  transition: .25s;
}

.generate:hover:not(:disabled) {
  transform: translateY(-2px);

  box-shadow:
    0 15px 45px rgba(124,92,246,.35),
    0 0 25px rgba(34,211,238,.12);
}

.generate:disabled {
  opacity: .55;
  cursor: wait;
}

@keyframes gradientMove {
  0%,100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.generate-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
}

/* ================================
   STATUS
================================ */

.status {
  display: none;

  margin-top: 14px;
  padding: 13px 15px;

  border-radius: 13px;

  font-size: 11px;
  line-height: 1.6;
}

.status.show {
  display: block;
}

.status.loading {
  color: #c8baff;
  background: rgba(139,92,246,.08);
  border: 1px solid rgba(139,92,246,.18);
}

.status.success {
  color: #6ee7b7;
  background: rgba(52,211,153,.07);
  border: 1px solid rgba(52,211,153,.17);
}

.status.error {
  color: #fb7185;
  background: rgba(244,63,94,.07);
  border: 1px solid rgba(244,63,94,.17);
}

.loader {
  display: inline-block;
  width: 13px;
  height: 13px;
  margin-right: 7px;

  border: 2px solid rgba(255,255,255,.15);
  border-top-color: currentColor;
  border-radius: 50%;

  vertical-align: -2px;

  animation: spin .7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ================================
   AUDIO STUDIO
================================ */

.audio-panel {
  display: none;
}

.audio-panel.show {
  display: block;
  animation: panelIn .45s ease;
}

@keyframes panelIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  margin-bottom: 18px;
}

.output-badge {
  padding: 6px 10px;

  border-radius: 20px;

  color: #65e7c0;
  background: rgba(52,211,153,.07);
  border: 1px solid rgba(52,211,153,.16);

  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
}

.track {
  width: 100%;
  max-width: 100%;
  min-width: 0;

  overflow: hidden;

  padding: 20px;

  background:
    radial-gradient(
      circle at 10% 20%,
      rgba(139,92,246,.10),
      transparent 35%
    ),
    rgba(5,6,12,.76);

  border: 1px solid var(--line);
  border-radius: 20px;
}

.track-info {
  width: 100%;
  min-width: 0;

  display: flex;
  align-items: center;

  gap: 14px;
}

.track-info > div:last-child {
  min-width: 0;
}

.track-name {
  min-width: 0;

  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  font-size: 13px;
  font-weight: 700;
}

.track-meta {
  margin-top: 4px;

  color: var(--muted);
  font-size: 10px;
}

/* waveform */

.waveform {
  width: 100%;
  max-width: 100%;
  min-width: 0;

  height: 58px;

  display: flex;
  align-items: center;
  justify-content: flex-start;

  gap: 3px;

  margin: 18px 0 12px;

  padding: 0 2px;

  overflow: hidden;
}

.bar {
  flex: 0 0 3px;

  width: 3px;
  min-width: 3px;
  max-width: 3px;

  min-height: 7px;

  border-radius: 10px;

  background:
    linear-gradient(
      to top,
      var(--purple),
      var(--cyan)
    );

  opacity: .5;
}

.bar.playing {
  animation: wave .8s ease-in-out infinite alternate;
}

@keyframes wave {
  from { transform: scaleY(.35); }
  to { transform: scaleY(1.15); }
}

/* progress */

.progress-area {
  position: relative;
  height: 5px;

  margin: 8px 0 9px;

  border-radius: 10px;

  background: #242638;

  cursor: pointer;
}

.progress-fill {
  width: 0%;
  height: 100%;

  border-radius: inherit;

  background: linear-gradient(90deg, var(--purple), var(--cyan));

  box-shadow: 0 0 12px rgba(34,211,238,.3);
}

.time-row {
  display: flex;
  justify-content: space-between;

  color: #6d7183;
  font-size: 9px;
}

/* player controls */

.player-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;

  margin-top: 16px;
}

.controls-left,
.controls-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.circle-btn {
  width: 37px;
  height: 37px;

  display: grid;
  place-items: center;

  border-radius: 50%;

  color: #b9bdca;

  background: #10121d;
  border: 1px solid var(--line);

  cursor: pointer;

  transition: .2s;
}

.circle-btn:hover {
  color: white;
  border-color: rgba(139,92,246,.5);
  background: rgba(139,92,246,.10);
}

.play-btn {
  width: 48px;
  height: 48px;

  color: white;

  background:
    linear-gradient(135deg, var(--purple), #6845d9);

  border-color: rgba(139,92,246,.8);

  box-shadow: 0 0 25px rgba(139,92,246,.22);
}

.play-btn:hover {
  background:
    linear-gradient(135deg, #9b6dff, #704de2);
}

/* volume */

.volume {
  display: flex;
  align-items: center;
  gap: 7px;
}

.volume input {
  width: 70px;
  accent-color: var(--purple);
}

.speed-mini {
  padding: 7px 9px;

  border-radius: 9px;

  color: #aaaebe;

  background: #10121d;
  border: 1px solid var(--line);

  font-size: 9px;

  cursor: pointer;
}

/* ================================
   DOWNLOADS
================================ */

.downloads {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;

  margin-top: 12px;
}

.download {
  height: 46px;

  border-radius: 13px;

  color: #bfc2cf;
  background: #0b0d15;

  border: 1px solid var(--line);

  cursor: pointer;

  font-family: inherit;
  font-size: 11px;
  font-weight: 600;

  transition: .2s;
}

.download:hover {
  color: white;
  border-color: rgba(34,211,238,.35);
  background: rgba(34,211,238,.06);
}

.download.primary:hover {
  border-color: rgba(52,211,153,.4);
  background: rgba(52,211,153,.06);
}

/* ================================
   FOOTER
================================ */

footer {
  text-align: center;

  margin-top: 30px;

  color: #505466;

  font-size: 9px;
  letter-spacing: .5px;
}

.footer-line {
  width: 50px;
  height: 1px;

  margin: 0 auto 13px;

  background: linear-gradient(
    90deg,
    transparent,
    var(--purple),
    transparent
  );
}

/* ================================
   MOBILE
================================ */

@media (max-width: 760px) {

  .app {
    width: calc(100% - 18px);
    max-width: 650px;

    padding-top: 10px;
  }

  .topbar {
    height: 60px;
    padding: 0 13px;
    border-radius: 17px;
  }

  .logo {
    width: 37px;
    height: 37px;
  }

  .brand-text span {
    display: none;
  }

  .hero {
    min-height: 245px;
    padding: 30px 22px;
    border-radius: 24px;
  }

  .hero-orb {
    right: -25px;
    top: 125px;
    opacity: .45;
    transform: scale(.7);
  }

  .workspace {
    grid-template-columns:
      minmax(0, 1fr);
  }

  .panel.full {
    grid-column: auto;
  }

  .panel {
    width: 100%;
    min-width: 0;

    padding: 17px;
    border-radius: 20px;
  }

  .track {
    width: 100%;
    min-width: 0;
    padding: 15px;
  }

  .waveform {
    width: 100%;
    max-width: 100%;

    height: 52px;

    gap: 2px;

    overflow: hidden;
  }

  .bar {
    flex: 0 0 3px;

    width: 3px;
    min-width: 3px;
    max-width: 3px;
  }
}

@media (max-width: 480px) {

  .app {
    width: calc(100% - 12px);
  }

  .panel {
    padding: 14px;
  }

  .track {
    padding: 14px;
  }

  .waveform {
    height: 48px;
    gap: 2px;
  }

  .bar {
    flex: 0 0 2px;

    width: 2px;
    min-width: 2px;
    max-width: 2px;
  }

  .player-controls {
    flex-wrap: wrap;
  }

  .controls-left {
    width: 100%;
    justify-content: center;
  }

  .controls-right {
    width: 100%;
    justify-content: space-between;
  }

  .volume input {
    width: 90px;
    max-width: 90px;
  }

  .downloads {
    grid-template-columns: 1fr;
  }

  .download {
    height: 48px;
  }
}
</style>
</head>

<body>

<div class="app">

  <!-- TOP BAR -->
  <div class="topbar">

    <div class="brand">

      <div class="logo">🎬</div>

      <div class="brand-text">
        <strong>Movie Recap AI</strong>
        <span>Voice Studio</span>
      </div>

    </div>

    <div class="live">
      <span class="live-dot"></span>
      AI ENGINE ONLINE
    </div>

  </div>


  <!-- HERO -->
  <section class="hero">

    <div class="hero-content">

      <div class="eyebrow">
        ✦ MICROSOFT NEURAL VOICE
      </div>

      <h1>
        Turn Your Story<br>
        Into a Voice.
      </h1>

      <p>
        Movie recap စာသားတွေကို cinematic Myanmar AI voice
        အဖြစ် ပြောင်းပြီး professional narration တစ်ခုလို
        ဖန်တီးလိုက်ပါ။
      </p>

    </div>

    <div class="hero-orb"></div>

  </section>


  <!-- WORKSPACE -->
  <div class="workspace">


    <!-- VOICE -->
    <section class="panel">

      <div class="panel-title">

        <div class="panel-title-left">
          <div class="panel-icon">🎤</div>

          <div>
            <strong>Voice Engine</strong><br>
            <small>ရွေးချယ်ပါ</small>
          </div>
        </div>

      </div>


      <div class="voice-grid">

        <button
          class="voice-card active"
          data-voice="thiha"
          onclick="selectVoice('thiha')">

          <div class="voice-top">

            <div class="voice-avatar">♂</div>

            <div class="check">✓</div>

          </div>

          <div class="voice-name">
            Thiha
          </div>

          <div class="voice-gender">
            Myanmar • ကျားအသံ
          </div>

        </button>


        <button
          class="voice-card"
          data-voice="nilar"
          onclick="selectVoice('nilar')">

          <div class="voice-top">

            <div class="voice-avatar">♀</div>

            <div class="check">✓</div>

          </div>

          <div class="voice-name">
            Nilar
          </div>

          <div class="voice-gender">
            Myanmar • မအသံ
          </div>

        </button>

      </div>

    </section>


    <!-- SPEED -->
    <section class="panel">

      <div class="panel-title">

        <div class="panel-title-left">

          <div class="panel-icon">⚡</div>

          <div>
            <strong>Voice Speed</strong><br>
            <small>အသံအမြန်နှုန်း</small>
          </div>

        </div>

      </div>


      <div class="speed-list" id="speedGrid"></div>

      <div class="speed-recommend">
        MOVIE RECAP RECOMMENDED →
        <b>1.4x</b>
      </div>

    </section>


    <!-- TEXT EDITOR -->
    <section class="panel full editor">

      <div class="panel-title">

        <div class="panel-title-left">

          <div class="panel-icon">✎</div>

          <div>
            <strong>Script Editor</strong><br>
            <small>သင့်ရဲ့ narration script</small>
          </div>

        </div>

        <small id="charCount">0 characters</small>

      </div>


      <div class="textarea-wrap">

        <textarea
          id="textInput"
          placeholder="Movie recap စာသားကို ဒီနေရာမှာ ရိုက်ထည့်ပါ...

ဥပမာ -

ဒီဇာတ်ကားမှာတော့ လူငယ်တစ်ယောက်ဟာ
မထင်မှတ်ထားတဲ့ အဖြစ်အပျက်တစ်ခုကြောင့်
သူ့ဘဝတစ်ခုလုံး ပြောင်းလဲသွားခဲ့ပါတယ်..."></textarea>

      </div>


      <div class="editor-bottom">

        <div class="tip">
          💡 “၊” “။” ပုဒ်ဖြတ်ပုဒ်ရပ်တွေ ထည့်ရင်
          narration ပိုသဘာဝကျပါတယ်။
        </div>

      </div>


      <button
        class="generate"
        id="generateBtn"
        onclick="generateTTS()">

        <span class="generate-inner">
          <span>✦</span>
          GENERATE CINEMATIC VOICE
          <span>→</span>
        </span>

      </button>


      <div class="status" id="statusBox"></div>

    </section>


    <!-- AUDIO OUTPUT -->
    <section class="panel full audio-panel" id="audioPanel">

      <div class="output-header">

        <div class="panel-title" style="margin:0">

          <div class="panel-title-left">

            <div class="panel-icon">🎧</div>

            <div>
              <strong>Studio Output</strong><br>
              <small>Generated narration</small>
            </div>

          </div>

        </div>

        <div class="output-badge">
          READY
        </div>

      </div>


      <div class="track">

        <div class="track-info">

          <div class="track-icon">
            🎬
          </div>

          <div>

            <div class="track-name" id="trackName">
              Movie Recap Narration
            </div>

            <div class="track-meta" id="trackMeta">
              Thiha • 1.4x • MP3
            </div>

          </div>

        </div>


        <!-- WAVEFORM -->
        <div class="waveform" id="waveform"></div>


        <!-- HIDDEN REAL AUDIO -->
        <audio id="audioElement"></audio>


        <!-- PROGRESS -->
        <div
          class="progress-area"
          id="progressArea">

          <div
            class="progress-fill"
            id="progressFill">
          </div>

        </div>


        <div class="time-row">

          <span id="currentTime">
            00:00
          </span>

          <span id="duration">
            00:00
          </span>

        </div>


        <!-- CONTROLS -->
        <div class="player-controls">

          <div class="controls-left">

            <button
              class="circle-btn"
              onclick="skipAudio(-5)">
              ↶
            </button>

            <button
              class="circle-btn play-btn"
              id="playBtn"
              onclick="togglePlay()">
              ▶
            </button>

            <button
              class="circle-btn"
              onclick="skipAudio(5)">
              ↷
            </button>

          </div>


          <div class="controls-right">

            <div class="volume">

              <span>🔊</span>

              <input
                type="range"
                id="volume"
                min="0"
                max="1"
                step=".01"
                value=".8">

            </div>

            <button
              class="speed-mini"
              onclick="cyclePlayerSpeed()"
              id="playerSpeed">
              1.0x
            </button>

          </div>

        </div>


        <!-- DOWNLOAD -->
        <div class="downloads">

          <button
            class="download primary"
            onclick="downloadAudio()">
            ↓ &nbsp; DOWNLOAD MP3
          </button>

          <button
            class="download"
            onclick="downloadTranscript()">
            ≡ &nbsp; TRANSCRIPT TXT
          </button>

        </div>

      </div>

    </section>

  </div>


  <footer>

    <div class="footer-line"></div>

    MOVIE RECAP AI STUDIO
    • POWERED BY EDGE NEURAL VOICES

  </footer>

</div>


<script>

/* ==========================================
   CONFIG
========================================== */

const VOICES = {

  thiha: {
    id: "my-MM-ThihaNeural",
    name: "Thiha",
    gender: "ကျား"
  },

  nilar: {
    id: "my-MM-NilarNeural",
    name: "Nilar",
    gender: "မ"
  }

};

const SPEED_OPTIONS =
  [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0];

const DEFAULT_VOICE = "thiha";
const DEFAULT_SPEED = 1.4;


/* ==========================================
   STATE
========================================== */

let currentVoice =
  localStorage.getItem("tts_voice") ||
  DEFAULT_VOICE;

let currentSpeed =
  parseFloat(
    localStorage.getItem("tts_speed")
  ) || DEFAULT_SPEED;

let lastAudioBlob = null;
let lastText = "";
let lastFilename = "";

let playerSpeed = 1.0;


/* ==========================================
   INIT
========================================== */

function init() {

  buildSpeedButtons();
  buildWaveform();

  document
    .querySelectorAll(".voice-card")
    .forEach(card => {

      card.classList.toggle(
        "active",
        card.dataset.voice === currentVoice
      );

    });


  const textarea =
    document.getElementById("textInput");

  textarea.addEventListener(
    "input",
    updateCharCount
  );


  const audio =
    document.getElementById("audioElement");


  audio.addEventListener(
    "timeupdate",
    updateProgress
  );


  audio.addEventListener(
    "loadedmetadata",
    () => {

      document.getElementById("duration")
        .textContent =
        formatTime(audio.duration);

    }
  );


  audio.addEventListener(
    "play",
    () => {

      document.getElementById("playBtn")
        .textContent = "Ⅱ";

      document
        .querySelectorAll(".bar")
        .forEach(bar =>
          bar.classList.add("playing")
        );

    }
  );


  audio.addEventListener(
    "pause",
    () => {

      document.getElementById("playBtn")
        .textContent = "▶";

      document
        .querySelectorAll(".bar")
        .forEach(bar =>
          bar.classList.remove("playing")
        );

    }
  );


  audio.addEventListener(
    "ended",
    () => {

      document.getElementById("playBtn")
        .textContent = "▶";

      document
        .querySelectorAll(".bar")
        .forEach(bar =>
          bar.classList.remove("playing")
        );

    }
  );


  document
    .getElementById("progressArea")
    .addEventListener(
      "click",
      seekAudio
    );


  document
    .getElementById("volume")
    .addEventListener(
      "input",
      e => {
        audio.volume =
          parseFloat(e.target.value);
      }
    );


  audio.volume = .8;

}


/* ==========================================
   SPEED BUTTONS
========================================== */

function buildSpeedButtons() {

  const grid =
    document.getElementById("speedGrid");

  grid.innerHTML = "";

  SPEED_OPTIONS.forEach(speed => {

    const btn =
      document.createElement("button");

    btn.className =
      "speed" +
      (
        speed === currentSpeed
        ? " active"
        : ""
      );

    btn.textContent =
      speed.toFixed(1) + "x";

    btn.onclick =
      () => selectSpeed(speed);

    grid.appendChild(btn);

  });

}


/* ==========================================
   VOICE
========================================== */

function selectVoice(key) {

  currentVoice = key;

  localStorage.setItem(
    "tts_voice",
    key
  );


  document
    .querySelectorAll(".voice-card")
    .forEach(card => {

      card.classList.toggle(
        "active",
        card.dataset.voice === key
      );

    });


  updateTrackPreview();

}


/* ==========================================
   SPEED
========================================== */

function selectSpeed(speed) {

  currentSpeed = speed;

  localStorage.setItem(
    "tts_speed",
    speed
  );


  document
    .querySelectorAll(".speed")
    .forEach(btn => {

      btn.classList.toggle(
        "active",
        parseFloat(
          btn.textContent
        ) === speed
      );

    });


  updateTrackPreview();

}


/* ==========================================
   TRACK PREVIEW
========================================== */

function updateTrackPreview() {

  const voice =
    VOICES[currentVoice];

  document.getElementById(
    "trackMeta"
  ).textContent =
    `${voice.name} • ${currentSpeed.toFixed(1)}x • MP3`;

}


/* ==========================================
   CHARACTER COUNT
========================================== */

function updateCharCount() {

  const value =
    document
      .getElementById("textInput")
      .value;

  document.getElementById(
    "charCount"
  ).textContent =
    value.length.toLocaleString() +
    " characters";

}


/* ==========================================
   WAVEFORM
========================================== */

function buildWaveform() {

  const waveform =
    document.getElementById("waveform");

  waveform.innerHTML = "";

  for (let i = 0; i < 90; i++) {

    const bar =
      document.createElement("div");

    bar.className = "bar";

    const height =
      8 + Math.random() * 42;

    bar.style.height =
      height + "px";

    bar.style.opacity =
      0.35 + Math.random() * 0.55;

    waveform.appendChild(bar);
  }
}


/* ==========================================
   GENERATE TTS
========================================== */

async function generateTTS() {

  const text =
    document
      .getElementById("textInput")
      .value
      .trim();


  if (!text) {

    showStatus(
      "error",
      "⚠️ အသံပြောင်းလိုသော စာသားကို အရင်ထည့်ပါ။"
    );

    return;

  }


  const btn =
    document.getElementById(
      "generateBtn"
    );

  btn.disabled = true;


  const voice =
    VOICES[currentVoice];


  showStatus(
    "loading",
    `<span class="loader"></span>
     ${voice.name} Neural Voice ဖြင့်
     ${currentSpeed.toFixed(1)}x narration
     ဖန်တီးနေပါသည်...`
  );


  try {

    const res =
      await fetch(
        "/api/tts",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify({
            text: text,
            voice: currentVoice,
            speed: currentSpeed
          })

        }
      );


    if (!res.ok) {

      const err =
        await res
          .json()
          .catch(() => ({}));

      throw new Error(
        err.error ||
        "Server Error"
      );

    }


    const blob =
      await res.blob();


    lastAudioBlob = blob;
    lastText = text;


    const timestamp =
      new Date()
        .toISOString()
        .replace(/[:.]/g, "-")
        .slice(0, 19);


    lastFilename =
      `Movie_Recap_${currentVoice}_${currentSpeed.toFixed(1)}x_${timestamp}`;


    const url =
  URL.createObjectURL(blob);

const audio =
  document.getElementById("audioElement");

if (audio.src) {
  try {
    URL.revokeObjectURL(audio.src);
  } catch (_) {}
}

audio.src = url;

audio.playbackRate = playerSpeed;

audio.load();


    audio.playbackRate =
      playerSpeed;


    document.getElementById(
      "audioPanel"
    ).classList.add("show");


    document.getElementById(
      "trackName"
    ).textContent =
      "Movie Recap Narration";


    updateTrackPreview();


    showStatus(
      "success",
      "✓ Narration ready — Studio Output မှာ နားထောင်နိုင်ပါပြီ။"
    );


    setTimeout(() => {

      document
        .getElementById("audioPanel")
        .scrollIntoView({
          behavior: "smooth",
          block: "center"
        });

    }, 150);


  } catch (err) {

    console.error(err);

    showStatus(
      "error",
      "❌ Audio generation မအောင်မြင်ပါ။ Server ကို စစ်ပြီး ပြန်စမ်းပါ။"
    );

  } finally {

    btn.disabled = false;

  }

}


/* ==========================================
   STATUS
========================================== */

function showStatus(type, message) {

  const box =
    document.getElementById(
      "statusBox"
    );

  box.className =
    "status show " + type;

  box.innerHTML = message;

}


/* ==========================================
   AUDIO PLAYER
========================================== */

function togglePlay() {

  const audio =
    document.getElementById(
      "audioElement"
    );


  if (!audio.src) return;


  if (audio.paused) {

    audio.play();

  } else {

    audio.pause();

  }

}


function skipAudio(seconds) {

  const audio =
    document.getElementById(
      "audioElement"
    );

  audio.currentTime =
    Math.max(
      0,
      Math.min(
        audio.duration || 0,
        audio.currentTime + seconds
      )
    );

}


function updateProgress() {

  const audio =
    document.getElementById(
      "audioElement"
    );


  if (!audio.duration) return;


  const percent =
    (audio.currentTime /
      audio.duration) * 100;


  document.getElementById(
    "progressFill"
  ).style.width =
    percent + "%";


  document.getElementById(
    "currentTime"
  ).textContent =
    formatTime(
      audio.currentTime
    );

}


function seekAudio(e) {

  const audio =
    document.getElementById(
      "audioElement"
    );


  if (!audio.duration) return;


  const rect =
    e.currentTarget.getBoundingClientRect();


  const percent =
    (e.clientX - rect.left) /
    rect.width;


  audio.currentTime =
    percent * audio.duration;

}


function formatTime(seconds) {

  if (!isFinite(seconds))
    return "00:00";


  const min =
    Math.floor(seconds / 60);

  const sec =
    Math.floor(seconds % 60);


  return String(min).padStart(2,"0")
    + ":" +
    String(sec).padStart(2,"0");

}


/* ==========================================
   PLAYER SPEED
========================================== */

function cyclePlayerSpeed() {

  const speeds =
    [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0];

  let index =
    speeds.indexOf(playerSpeed);

  index =
    (index + 1) % speeds.length;

  playerSpeed =
    speeds[index];


  const audio =
    document.getElementById(
      "audioElement"
    );

  audio.playbackRate =
    playerSpeed;


  document.getElementById(
    "playerSpeed"
  ).textContent =
    playerSpeed.toFixed(1) + "x";

}


/* ==========================================
   DOWNLOAD MP3
========================================== */

function downloadAudio() {

  if (!lastAudioBlob)
    return;


  const a =
    document.createElement("a");


  a.href =
    URL.createObjectURL(
      lastAudioBlob
    );


  a.download =
    lastFilename + ".mp3";


  document.body.appendChild(a);

  a.click();

  a.remove();

}


/* ==========================================
   DOWNLOAD TRANSCRIPT
========================================== */

function downloadTranscript() {

  if (!lastText)
    return;


  const voice =
    VOICES[currentVoice];


  const content =
`MOVIE RECAP AI STUDIO
=====================

Voice  : ${voice.name} (${voice.gender})
Speed  : ${currentSpeed.toFixed(1)}x
Created: ${new Date().toLocaleString()}

=====================

${lastText}

=====================

Generated by Movie Recap AI Studio
`;


  const blob =
    new Blob(
      [content],
      {
        type:
          "text/plain;charset=utf-8"
      }
    );


  const a =
    document.createElement("a");


  a.href =
    URL.createObjectURL(blob);


  a.download =
    "Transcript_" +
    lastFilename +
    ".txt";


  document.body.appendChild(a);

  a.click();

  a.remove();

}


/* ==========================================
   START
========================================== */

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
