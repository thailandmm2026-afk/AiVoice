# -*- coding: utf-8 -*-
"""
Movie Recap TTS Web App
Backend: Flask + edge-tts
Frontend: Modern Myanmar UI (matches provided design)
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
        "gender": "ကျားအသံ"
    },
    "nilar": {
        "id": "my-MM-NilarNeural",
        "name": "Nilar",
        "gender": "မအသံ"
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
# FRONTEND (Single Page) - Matches provided design
# =========================================================

HTML_PAGE = r'''<!DOCTYPE html>
<html lang="my">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#070812">
<title>Movie Recap TTS · AI Voice Studio</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Myanmar:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #05060f;
  --bg2: #0a0c18;
  --panel: rgba(12, 14, 26, 0.85);
  --panel-border: rgba(139, 92, 246, 0.18);
  --line: rgba(255,255,255,0.08);
  --purple: #8b5cf6;
  --violet: #a855f7;
  --cyan: #22d3ee;
  --blue: #3b82f6;
  --pink: #ec4899;
  --green: #34d399;
  --text: #f1f5f9;
  --muted: #94a3b8;
  --radius: 20px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  width: 100%;
  min-height: 100%;
  overflow-x: hidden;
  scroll-behavior: smooth;
}

body {
  color: var(--text);
  font-family: Inter, "Noto Sans Myanmar", system-ui, sans-serif;
  background: 
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(139,92,246,0.25), transparent),
    radial-gradient(ellipse 60% 40% at 90% 20%, rgba(34,211,238,0.12), transparent),
    radial-gradient(ellipse 50% 30% at 10% 80%, rgba(168,85,247,0.1), transparent),
    #05060f;
  line-height: 1.5;
}

/* ========== TOPBAR ========== */
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: rgba(5,6,15,0.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--line);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 18px;
  background: linear-gradient(135deg, rgba(139,92,246,0.4), rgba(34,211,238,0.2));
  border: 1px solid rgba(139,92,246,0.5);
  box-shadow: 0 0 20px rgba(139,92,246,0.3);
}

.brand-text strong {
  display: block;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.3px;
  background: linear-gradient(90deg, #fff, #c4b5fd);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-text span {
  display: block;
  font-size: 10px;
  color: var(--muted);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  margin-top: 1px;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.online-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(52,211,153,0.1);
  border: 1px solid rgba(52,211,153,0.3);
  color: #6ee7b7;
  font-size: 11px;
  font-weight: 600;
}

.online-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 8px #34d399;
  animation: pulse 1.6s infinite;
}

@keyframes pulse {
  50% { opacity: 0.4; transform: scale(0.75); }
}

.menu-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--line);
  color: var(--muted);
  display: grid;
  place-items: center;
  cursor: pointer;
  font-size: 16px;
}

/* ========== APP CONTAINER ========== */
.app {
  width: min(980px, calc(100% - 24px));
  margin: 0 auto;
  padding: 20px 0 60px;
}

/* ========== HERO ========== */
.hero {
  position: relative;
  overflow: hidden;
  border-radius: 24px;
  border: 1px solid rgba(139,92,246,0.25);
  background: 
    radial-gradient(circle at 85% 30%, rgba(34,211,238,0.15), transparent 40%),
    radial-gradient(circle at 10% 80%, rgba(139,92,246,0.2), transparent 45%),
    linear-gradient(145deg, rgba(18,16,36,0.95), rgba(8,9,18,0.98));
  padding: 36px 32px;
  margin-bottom: 18px;
  box-shadow: 0 25px 80px rgba(0,0,0,0.4);
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 20px;
  align-items: center;
}

.hero-content { position: relative; z-index: 2; }

.hero h1 {
  font-size: clamp(28px, 5.5vw, 42px);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -1px;
  margin-bottom: 14px;
}

.hero h1 .line1 { color: #fff; display: block; }
.hero h1 .line2 {
  background: linear-gradient(90deg, #a78bfa, #22d3ee, #60a5fa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: block;
}

.hero p {
  color: #a1a1b5;
  font-size: 13.5px;
  line-height: 1.75;
  max-width: 420px;
  margin-bottom: 22px;
}

.feature-row {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}

.feature {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 70px;
}

.feature-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 18px;
  background: rgba(139,92,246,0.12);
  border: 1px solid rgba(139,92,246,0.25);
}

.feature strong {
  font-size: 11px;
  font-weight: 700;
  color: #e2e8f0;
}

.feature span {
  font-size: 9px;
  color: var(--muted);
}

.hero-visual {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 180px;
}

.mic-scene {
  position: relative;
  width: 200px;
  height: 180px;
}

.mic {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 70px;
  height: 110px;
  background: linear-gradient(180deg, #1e1b4b, #312e81);
  border-radius: 35px 35px 20px 20px;
  border: 2px solid rgba(139,92,246,0.6);
  box-shadow: 
    0 0 40px rgba(139,92,246,0.4),
    0 0 80px rgba(34,211,238,0.15),
    inset 0 0 30px rgba(34,211,238,0.1);
  z-index: 3;
}

.mic::before {
  content: "";
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: 36px;
  height: 50px;
  border-radius: 18px;
  background: linear-gradient(180deg, #4c1d95, #1e1b4b);
  border: 1px solid rgba(168,85,247,0.5);
}

.mic::after {
  content: "";
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 28px;
  height: 16px;
  background: #1e1b4b;
  border-radius: 0 0 8px 8px;
  border: 1px solid rgba(139,92,246,0.4);
}

.clapper {
  position: absolute;
  left: 8px;
  top: 20px;
  width: 70px;
  height: 50px;
  background: linear-gradient(135deg, #1e1b4b, #312e81);
  border-radius: 6px;
  border: 1px solid rgba(139,92,246,0.5);
  box-shadow: 0 0 25px rgba(139,92,246,0.25);
  z-index: 2;
  transform: rotate(-12deg);
}

.clapper::before {
  content: "SCENE  TAKE  ROLL";
  position: absolute;
  top: 6px;
  left: 6px;
  right: 6px;
  font-size: 6px;
  color: #a78bfa;
  letter-spacing: 0.5px;
}

.reel {
  position: absolute;
  right: 0;
  bottom: 10px;
  width: 65px;
  height: 65px;
  border-radius: 50%;
  background: 
    radial-gradient(circle at 50% 50%, #0f172a 30%, transparent 31%),
    radial-gradient(circle at 50% 50%, transparent 38%, #312e81 39%, #312e81 48%, transparent 49%),
    linear-gradient(135deg, #1e1b4b, #4c1d95);
  border: 2px solid rgba(139,92,246,0.5);
  box-shadow: 0 0 30px rgba(139,92,246,0.3);
  z-index: 1;
}

.glow-ring {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 160px;
  height: 160px;
  border-radius: 50%;
  border: 1px solid rgba(34,211,238,0.25);
  box-shadow: 0 0 40px rgba(34,211,238,0.1);
  animation: floatOrb 5s ease-in-out infinite;
}

@keyframes floatOrb {
  50% { transform: translate(-50%, -55%) scale(1.05); }
}

/* ========== WORKSPACE GRID ========== */
.workspace {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius);
  padding: 18px;
  backdrop-filter: blur(16px);
  box-shadow: 0 15px 50px rgba(0,0,0,0.3);
}

.panel.full { grid-column: 1 / -1; }

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-icon {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 15px;
  background: rgba(139,92,246,0.12);
  border: 1px solid rgba(139,92,246,0.25);
}

.panel-title strong {
  font-size: 13px;
  font-weight: 700;
}

.panel-title small {
  display: block;
  font-size: 10px;
  color: var(--muted);
  margin-top: 1px;
}

/* ========== VOICE SELECTOR ========== */
.voice-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.voice-card {
  position: relative;
  padding: 16px 14px;
  border-radius: 16px;
  background: rgba(5,6,15,0.7);
  border: 1px solid var(--line);
  cursor: pointer;
  transition: all 0.25s;
  text-align: left;
  color: inherit;
}

.voice-card:hover {
  border-color: rgba(139,92,246,0.45);
  transform: translateY(-2px);
}

.voice-card.active {
  border-color: rgba(139,92,246,0.85);
  background: 
    radial-gradient(circle at 15% 20%, rgba(139,92,246,0.22), transparent 55%),
    rgba(15,12,30,0.95);
  box-shadow: 0 0 0 1px rgba(139,92,246,0.2), 0 0 30px rgba(139,92,246,0.15);
}

.voice-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.voice-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 18px;
  background: linear-gradient(135deg, rgba(139,92,246,0.35), rgba(34,211,238,0.1));
  border: 1px solid rgba(139,92,246,0.4);
}

.voice-card:nth-child(2) .voice-avatar {
  background: linear-gradient(135deg, rgba(236,72,153,0.3), rgba(139,92,246,0.1));
  border-color: rgba(236,72,153,0.4);
}

.check {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid #3f4456;
  display: grid;
  place-items: center;
  font-size: 10px;
  color: transparent;
}

.voice-card.active .check {
  background: var(--purple);
  border-color: var(--purple);
  color: #fff;
  box-shadow: 0 0 12px rgba(139,92,246,0.5);
}

.voice-name {
  font-size: 14px;
  font-weight: 700;
}

.voice-gender {
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}

.voice-id {
  font-size: 9px;
  color: #64748b;
  margin-top: 6px;
  font-family: ui-monospace, monospace;
}

/* ========== SPEED ========== */
.speed-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.speed-btn {
  padding: 10px 4px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(5,6,15,0.7);
  color: #94a3b8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.speed-btn:hover {
  border-color: rgba(34,211,238,0.4);
  color: #fff;
}

.speed-btn.active {
  color: #fff;
  background: linear-gradient(135deg, rgba(139,92,246,0.3), rgba(34,211,238,0.1));
  border-color: rgba(139,92,246,0.7);
  box-shadow: 0 0 18px rgba(139,92,246,0.15);
}

.speed-note {
  margin-top: 12px;
  font-size: 10px;
  color: var(--muted);
}

.speed-note b {
  color: var(--cyan);
}

/* ========== SCRIPT EDITOR ========== */
.editor-panel {
  margin-top: 0;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.04);
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: 0.2s;
}

.action-btn:hover {
  border-color: rgba(139,92,246,0.4);
  color: #fff;
  background: rgba(139,92,246,0.1);
}

textarea {
  width: 100%;
  min-height: 160px;
  resize: vertical;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(4,5,12,0.75);
  color: #e2e8f0;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.8;
  outline: none;
  transition: 0.25s;
}

textarea:focus {
  border-color: rgba(139,92,246,0.6);
  box-shadow: 0 0 0 3px rgba(139,92,246,0.1);
}

textarea::placeholder {
  color: #4b5563;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.char-count {
  font-size: 11px;
  color: #64748b;
}

.tip {
  font-size: 10px;
  color: #64748b;
}

/* ========== GENERATE BUTTON ========== */
.generate-btn {
  width: 100%;
  height: 54px;
  margin-top: 16px;
  border: none;
  border-radius: 14px;
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  background: linear-gradient(100deg, #7c3aed, #8b5cf6, #3b82f6, #06b6d4);
  background-size: 250% 100%;
  animation: gradientShift 4s ease infinite;
  box-shadow: 0 10px 30px rgba(124,58,237,0.3);
  transition: 0.25s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 14px 40px rgba(124,58,237,0.4);
}

.generate-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

/* ========== STATUS ========== */
.status {
  display: none;
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.5;
}

.status.show { display: flex; align-items: center; gap: 8px; }

.status.loading {
  color: #c4b5fd;
  background: rgba(139,92,246,0.1);
  border: 1px solid rgba(139,92,246,0.2);
}

.status.success {
  color: #6ee7b7;
  background: rgba(52,211,153,0.08);
  border: 1px solid rgba(52,211,153,0.2);
}

.status.error {
  color: #fb7185;
  background: rgba(244,63,94,0.08);
  border: 1px solid rgba(244,63,94,0.2);
}

.loader {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.15);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ========== AUDIO OUTPUT ========== */
.audio-panel {
  display: none;
  margin-top: 16px;
}

.audio-panel.show {
  display: block;
  animation: fadeUp 0.4s ease;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.output-badge {
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.8px;
  color: #6ee7b7;
  background: rgba(52,211,153,0.1);
  border: 1px solid rgba(52,211,153,0.25);
}

.track-card {
  background: rgba(5,6,15,0.75);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px;
}

.track-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.track-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 22px;
  background: linear-gradient(135deg, rgba(139,92,246,0.25), rgba(34,211,238,0.1));
  border: 1px solid rgba(139,92,246,0.35);
}

.track-name {
  font-size: 14px;
  font-weight: 700;
}

.track-meta {
  font-size: 11px;
  color: var(--muted);
  margin-top: 3px;
}

/* Waveform */
.waveform {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 2.5px;
  margin: 14px 0 12px;
  overflow: hidden;
}

.bar {
  flex: 0 0 3px;
  width: 3px;
  min-height: 6px;
  border-radius: 4px;
  background: linear-gradient(to top, var(--purple), var(--cyan));
  opacity: 0.55;
}

.bar.playing {
  animation: wave 0.75s ease-in-out infinite alternate;
}

@keyframes wave {
  from { transform: scaleY(0.4); }
  to { transform: scaleY(1.2); }
}

/* Progress */
.progress-wrap {
  position: relative;
  height: 6px;
  background: #1e2235;
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 6px;
}

.progress-fill {
  height: 100%;
  width: 0%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--purple), var(--cyan));
  box-shadow: 0 0 10px rgba(34,211,238,0.35);
  position: relative;
}

.progress-fill::after {
  content: "";
  position: absolute;
  right: -5px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 8px rgba(34,211,238,0.5);
}

.time-row {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #64748b;
  margin-bottom: 14px;
}

/* Controls */
.player-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ctrl-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: #10131f;
  color: #94a3b8;
  display: grid;
  place-items: center;
  cursor: pointer;
  font-size: 13px;
  transition: 0.2s;
}

.ctrl-btn:hover {
  color: #fff;
  border-color: rgba(139,92,246,0.5);
  background: rgba(139,92,246,0.12);
}

.play-btn {
  width: 48px;
  height: 48px;
  font-size: 16px;
  color: #fff;
  background: linear-gradient(135deg, var(--purple), #6d28d9);
  border-color: rgba(139,92,246,0.8);
  box-shadow: 0 0 20px rgba(139,92,246,0.3);
}

.play-btn:hover {
  background: linear-gradient(135deg, #a78bfa, #7c3aed);
}

.right-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.volume-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.volume-wrap input[type="range"] {
  width: 80px;
  accent-color: var(--purple);
  height: 4px;
}

.speed-select {
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: #10131f;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

/* Downloads */
.downloads {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 16px;
}

.dl-btn {
  height: 46px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #0b0d16;
  color: #cbd5e1;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: 0.2s;
}

.dl-btn:hover {
  color: #fff;
  border-color: rgba(34,211,238,0.4);
  background: rgba(34,211,238,0.08);
}

.dl-btn.primary:hover {
  border-color: rgba(52,211,153,0.45);
  background: rgba(52,211,153,0.08);
}

/* Footer */
footer {
  text-align: center;
  margin-top: 32px;
  color: #475569;
  font-size: 10px;
  letter-spacing: 0.3px;
}

.footer-line {
  width: 48px;
  height: 1px;
  margin: 0 auto 12px;
  background: linear-gradient(90deg, transparent, var(--purple), transparent);
}

/* ========== RESPONSIVE ========== */
@media (max-width: 760px) {
  .hero-grid { grid-template-columns: 1fr; }
  .hero-visual { display: none; }
  .workspace { grid-template-columns: 1fr; }
  .speed-grid { grid-template-columns: repeat(4, 1fr); }
  .downloads { grid-template-columns: 1fr; }
  .player-row { flex-direction: column; align-items: stretch; }
  .controls { justify-content: center; }
  .right-controls { justify-content: space-between; }
}

@media (max-width: 480px) {
  .app { width: calc(100% - 16px); }
  .topbar { padding: 10px 14px; }
  .hero { padding: 24px 18px; }
  .panel { padding: 14px; }
  .voice-grid { grid-template-columns: 1fr; }
  .feature-row { gap: 12px; }
}
</style>
</head>
<body>

<!-- TOPBAR -->
<header class="topbar">
  <div class="brand">
    <div class="logo">🎬</div>
    <div class="brand-text">
      <strong>MOVIE RECAP TTS</strong>
      <span>AI Voice Studio</span>
    </div>
  </div>
  <div class="top-right">
    <div class="online-badge">
      <span class="online-dot"></span>
      ONLINE
    </div>
    <button class="menu-btn" title="Menu">☰</button>
  </div>
</header>

<div class="app">

  <!-- HERO -->
  <section class="hero">
    <div class="hero-grid">
      <div class="hero-content">
        <h1>
          <span class="line1">TURN YOUR STORY</span>
          <span class="line2">INTO A CINEMATIC VOICE</span>
        </h1>
        <p>
          Movie recap script ကို professional AI voice ဖြင့်
          natural narration အဖြစ် ပြောင်းလိုက်ပါ။
        </p>
        <div class="feature-row">
          <div class="feature">
            <div class="feature-icon">⚡</div>
            <strong>FAST</strong>
            <span>High Speed</span>
          </div>
          <div class="feature">
            <div class="feature-icon">〰</div>
            <strong>NATURAL</strong>
            <span>Neural Voice</span>
          </div>
          <div class="feature">
            <div class="feature-icon">🛡</div>
            <strong>SECURE</strong>
            <span>100% Safe</span>
          </div>
        </div>
      </div>
      <div class="hero-visual">
        <div class="mic-scene">
          <div class="glow-ring"></div>
          <div class="clapper"></div>
          <div class="mic"></div>
          <div class="reel"></div>
        </div>
      </div>
    </div>
  </section>

  <!-- WORKSPACE -->
  <div class="workspace">

    <!-- VOICE SELECTOR -->
    <section class="panel">
      <div class="panel-header">
        <div class="panel-title">
          <div class="panel-icon">🎤</div>
          <div>
            <strong>VOICE SELECTOR</strong>
            <small>အသံရွေးချယ်ပါ</small>
          </div>
        </div>
      </div>
      <div class="voice-grid">
        <button class="voice-card active" data-voice="thiha" onclick="selectVoice('thiha')">
          <div class="voice-top">
            <div class="voice-avatar">♂</div>
            <div class="check">✓</div>
          </div>
          <div class="voice-name">Thiha</div>
          <div class="voice-gender">ကျားအသံ</div>
          <div class="voice-id">my-MM-ThihaNeural</div>
        </button>
        <button class="voice-card" data-voice="nilar" onclick="selectVoice('nilar')">
          <div class="voice-top">
            <div class="voice-avatar">♀</div>
            <div class="check">✓</div>
          </div>
          <div class="voice-name">Nilar</div>
          <div class="voice-gender">မအသံ</div>
          <div class="voice-id">my-MM-NilarNeural</div>
        </button>
      </div>
    </section>

    <!-- VOICE SPEED -->
    <section class="panel">
      <div class="panel-header">
        <div class="panel-title">
          <div class="panel-icon">⚡</div>
          <div>
            <strong>VOICE SPEED</strong>
            <small>အသံအမြန်နှုန်း</small>
          </div>
        </div>
      </div>
      <div class="speed-grid" id="speedGrid"></div>
      <div class="speed-note">
        💡 MOVIE RECAP အတွက် အကြံပြုချက်: <b>1.4x</b>
      </div>
    </section>

    <!-- SCRIPT INPUT -->
    <section class="panel full editor-panel">
      <div class="panel-header">
        <div class="panel-title">
          <div class="panel-icon">✎</div>
          <div>
            <strong>SCRIPT / TEXT INPUT</strong>
            <small>သင့်ရဲ့ narration script</small>
          </div>
        </div>
        <div class="editor-actions">
          <button class="action-btn" onclick="pasteText()">📋 PASTE</button>
          <button class="action-btn" onclick="clearText()">🗑 CLEAR</button>
        </div>
      </div>

      <textarea
        id="textInput"
        placeholder="အသံပြောင်းလိုသော စာသားကို ဒီနေရာတွင် ရိုက်ထည့်ပါ...

ဥပမာ -
ဒီဇာတ်ကားမှာတော့ လူငယ်တစ်ယောက်ဟာ
မထင်မှတ်ထားတဲ့ အဖြစ်အပျက်တစ်ခုကြောင့်
သူ့ဘဝတစ်ခုလုံး ပြောင်းလဲသွားခဲ့ပါတယ်...

💡 “၊” “။” ပုဒ်ဖြတ်ပုဒ်ရပ်တွေ ထည့်ရင် narration ပိုသဘာဝကျပါတယ်။"></textarea>

      <div class="editor-footer">
        <div class="char-count" id="charCount">0 characters</div>
        <div class="tip">Microsoft Edge Neural Voices</div>
      </div>

      <button class="generate-btn" id="generateBtn" onclick="generateTTS()">
        <span>〰</span>
        GENERATE CINEMATIC VOICE
        <span>→</span>
      </button>

      <div class="status" id="statusBox"></div>
    </section>

    <!-- STUDIO OUTPUT -->
    <section class="panel full audio-panel" id="audioPanel">
      <div class="panel-header">
        <div class="panel-title">
          <div class="panel-icon">🎧</div>
          <div>
            <strong>STUDIO OUTPUT</strong>
            <small>Generated narration</small>
          </div>
        </div>
        <div class="output-badge">READY</div>
      </div>

      <div class="track-card">
        <div class="track-header">
          <div class="track-icon">🎬</div>
          <div>
            <div class="track-name" id="trackName">Movie Recap Narration</div>
            <div class="track-meta" id="trackMeta">Thiha • 1.4x • MP3</div>
          </div>
        </div>

        <div class="waveform" id="waveform"></div>

        <audio id="audioElement"></audio>

        <div class="progress-wrap" id="progressArea">
          <div class="progress-fill" id="progressFill"></div>
        </div>

        <div class="time-row">
          <span id="currentTime">00:00</span>
          <span id="duration">00:00</span>
        </div>

        <div class="player-row">
          <div class="controls">
            <button class="ctrl-btn" onclick="seekTo(0)" title="Start">⏮</button>
            <button class="ctrl-btn" onclick="skipAudio(-5)" title="-5s">↶5</button>
            <button class="ctrl-btn play-btn" id="playBtn" onclick="togglePlay()">▶</button>
            <button class="ctrl-btn" onclick="skipAudio(5)" title="+5s">↷5</button>
            <button class="ctrl-btn" onclick="seekToEnd()" title="End">⏭</button>
          </div>

          <div class="right-controls">
            <div class="volume-wrap">
              <span style="font-size:14px">🔊</span>
              <input type="range" id="volume" min="0" max="1" step="0.01" value="0.85">
            </div>
            <select class="speed-select" id="playerSpeedSelect" onchange="setPlayerSpeed(this.value)">
              <option value="0.8">0.8x</option>
              <option value="1.0" selected>1.0x</option>
              <option value="1.2">1.2x</option>
              <option value="1.4">1.4x</option>
              <option value="1.6">1.6x</option>
              <option value="1.8">1.8x</option>
              <option value="2.0">2.0x</option>
            </select>
          </div>
        </div>

        <div class="downloads">
          <button class="dl-btn primary" onclick="downloadAudio()">↓ DOWNLOAD MP3</button>
          <button class="dl-btn" onclick="downloadTranscript()">≡ TRANSCRIPT TXT</button>
        </div>
      </div>
    </section>

  </div>

  <footer>
    <div class="footer-line"></div>
    Movie Recap TTS Web · Powered by Microsoft Edge Neural Voices<br>
    Thiha & Nilar Myanmar AI Voices
  </footer>

</div>

<script>
/* ========== CONFIG ========== */
const VOICES = {
  thiha: { id: "my-MM-ThihaNeural", name: "Thiha", gender: "ကျားအသံ" },
  nilar: { id: "my-MM-NilarNeural", name: "Nilar", gender: "မအသံ" }
};
const SPEED_OPTIONS = [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0];
const DEFAULT_VOICE = "thiha";
const DEFAULT_SPEED = 1.4;

/* ========== STATE ========== */
let currentVoice = localStorage.getItem("tts_voice") || DEFAULT_VOICE;
let currentSpeed = parseFloat(localStorage.getItem("tts_speed")) || DEFAULT_SPEED;
let lastAudioBlob = null;
let lastText = "";
let lastFilename = "";
let playerSpeed = 1.0;

/* ========== INIT ========== */
function init() {
  buildSpeedButtons();
  buildWaveform();

  document.querySelectorAll(".voice-card").forEach(card => {
    card.classList.toggle("active", card.dataset.voice === currentVoice);
  });

  document.getElementById("textInput").addEventListener("input", updateCharCount);

  const audio = document.getElementById("audioElement");

  audio.addEventListener("timeupdate", updateProgress);
  audio.addEventListener("loadedmetadata", () => {
    document.getElementById("duration").textContent = formatTime(audio.duration);
  });
  audio.addEventListener("play", () => {
    document.getElementById("playBtn").textContent = "Ⅱ";
    document.querySelectorAll(".bar").forEach(b => b.classList.add("playing"));
  });
  audio.addEventListener("pause", () => {
    document.getElementById("playBtn").textContent = "▶";
    document.querySelectorAll(".bar").forEach(b => b.classList.remove("playing"));
  });
  audio.addEventListener("ended", () => {
    document.getElementById("playBtn").textContent = "▶";
    document.querySelectorAll(".bar").forEach(b => b.classList.remove("playing"));
  });

  document.getElementById("progressArea").addEventListener("click", seekAudio);
  document.getElementById("volume").addEventListener("input", e => {
    audio.volume = parseFloat(e.target.value);
  });
  audio.volume = 0.85;

  updateTrackPreview();
}

/* ========== SPEED BUTTONS ========== */
function buildSpeedButtons() {
  const grid = document.getElementById("speedGrid");
  grid.innerHTML = "";
  SPEED_OPTIONS.forEach(speed => {
    const btn = document.createElement("button");
    btn.className = "speed-btn" + (speed === currentSpeed ? " active" : "");
    btn.textContent = speed.toFixed(1) + "x";
    btn.onclick = () => selectSpeed(speed);
    grid.appendChild(btn);
  });
}

/* ========== VOICE ========== */
function selectVoice(key) {
  currentVoice = key;
  localStorage.setItem("tts_voice", key);
  document.querySelectorAll(".voice-card").forEach(card => {
    card.classList.toggle("active", card.dataset.voice === key);
  });
  updateTrackPreview();
}

/* ========== SPEED ========== */
function selectSpeed(speed) {
  currentSpeed = speed;
  localStorage.setItem("tts_speed", speed);
  document.querySelectorAll(".speed-btn").forEach(btn => {
    btn.classList.toggle("active", parseFloat(btn.textContent) === speed);
  });
  updateTrackPreview();
}

function updateTrackPreview() {
  const voice = VOICES[currentVoice];
  document.getElementById("trackMeta").textContent =
    `${voice.name} • ${currentSpeed.toFixed(1)}x • MP3`;
}

/* ========== CHAR COUNT ========== */
function updateCharCount() {
  const val = document.getElementById("textInput").value;
  document.getElementById("charCount").textContent =
    val.length.toLocaleString() + " characters";
}

/* ========== PASTE / CLEAR ========== */
async function pasteText() {
  try {
    const text = await navigator.clipboard.readText();
    const ta = document.getElementById("textInput");
    ta.value = text;
    updateCharCount();
    ta.focus();
  } catch (e) {
    showStatus("error", "Clipboard ဖတ်မရပါ။ စာသားကို ကိုယ်တိုင် paste လုပ်ပါ။");
  }
}

function clearText() {
  document.getElementById("textInput").value = "";
  updateCharCount();
}

/* ========== WAVEFORM ========== */
function buildWaveform() {
  const waveform = document.getElementById("waveform");
  waveform.innerHTML = "";
  for (let i = 0; i < 100; i++) {
    const bar = document.createElement("div");
    bar.className = "bar";
    const h = 8 + Math.random() * 40;
    bar.style.height = h + "px";
    bar.style.opacity = 0.35 + Math.random() * 0.5;
    bar.style.animationDelay = (Math.random() * 0.6) + "s";
    waveform.appendChild(bar);
  }
}

/* ========== GENERATE TTS ========== */
async function generateTTS() {
  const text = document.getElementById("textInput").value.trim();
  if (!text) {
    showStatus("error", "⚠️ အသံပြောင်းလိုသော စာသားကို အရင်ထည့်ပါ။");
    return;
  }

  const btn = document.getElementById("generateBtn");
  btn.disabled = true;
  const voice = VOICES[currentVoice];

  showStatus("loading",
    `<span class="loader"></span> ${voice.name} Neural Voice ဖြင့် ${currentSpeed.toFixed(1)}x narration ဖန်တီးနေပါသည်...`
  );

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
      throw new Error(err.error || "Server Error");
    }

    const blob = await res.blob();
    lastAudioBlob = blob;
    lastText = text;

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    lastFilename = `Movie_Recap_${currentVoice}_${currentSpeed.toFixed(1)}x_${timestamp}`;

    const url = URL.createObjectURL(blob);
    const audio = document.getElementById("audioElement");
    if (audio.src) {
      try { URL.revokeObjectURL(audio.src); } catch (_) {}
    }
    audio.src = url;
    audio.playbackRate = playerSpeed;
    audio.load();

    document.getElementById("audioPanel").classList.add("show");
    document.getElementById("trackName").textContent = "Movie Recap Narration";
    updateTrackPreview();

    showStatus("success", "✓ Narration ready — Studio Output မှာ နားထောင်နိုင်ပါပြီ။");

    setTimeout(() => {
      document.getElementById("audioPanel").scrollIntoView({ behavior: "smooth", block: "center" });
    }, 150);

  } catch (err) {
    console.error(err);
    showStatus("error", "❌ Audio generation မအောင်မြင်ပါ။ Server ကို စစ်ပြီး ပြန်စမ်းပါ။");
  } finally {
    btn.disabled = false;
  }
}

/* ========== STATUS ========== */
function showStatus(type, message) {
  const box = document.getElementById("statusBox");
  box.className = "status show " + type;
  box.innerHTML = message;
}

/* ========== PLAYER ========== */
function togglePlay() {
  const audio = document.getElementById("audioElement");
  if (!audio.src) return;
  if (audio.paused) audio.play();
  else audio.pause();
}

function skipAudio(seconds) {
  const audio = document.getElementById("audioElement");
  audio.currentTime = Math.max(0, Math.min(audio.duration || 0, audio.currentTime + seconds));
}

function seekTo(t) {
  const audio = document.getElementById("audioElement");
  audio.currentTime = t;
}

function seekToEnd() {
  const audio = document.getElementById("audioElement");
  if (audio.duration) audio.currentTime = audio.duration - 0.1;
}

function updateProgress() {
  const audio = document.getElementById("audioElement");
  if (!audio.duration) return;
  const percent = (audio.currentTime / audio.duration) * 100;
  document.getElementById("progressFill").style.width = percent + "%";
  document.getElementById("currentTime").textContent = formatTime(audio.currentTime);
}

function seekAudio(e) {
  const audio = document.getElementById("audioElement");
  if (!audio.duration) return;
  const rect = e.currentTarget.getBoundingClientRect();
  const percent = (e.clientX - rect.left) / rect.width;
  audio.currentTime = percent * audio.duration;
}

function formatTime(seconds) {
  if (!isFinite(seconds)) return "00:00";
  const min = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);
  return String(min).padStart(2, "0") + ":" + String(sec).padStart(2, "0");
}

function setPlayerSpeed(val) {
  playerSpeed = parseFloat(val);
  document.getElementById("audioElement").playbackRate = playerSpeed;
}

/* ========== DOWNLOAD ========== */
function downloadAudio() {
  if (!lastAudioBlob) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(lastAudioBlob);
  a.download = lastFilename + ".mp3";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function downloadTranscript() {
  if (!lastText) return;
  const voice = VOICES[currentVoice];
  const content = `MOVIE RECAP AI STUDIO
=====================

Voice  : ${voice.name} (${voice.gender})
Speed  : ${currentSpeed.toFixed(1)}x
Created: ${new Date().toLocaleString()}

=====================

${lastText}

=====================

Generated by Movie Recap TTS · AI Voice Studio
`;
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "Transcript_" + lastFilename + ".txt";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/* ========== START ========== */
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
