# 🎬 Movie Recap TTS Web

Myanmar AI Voice (Thiha + Nilar) Text-to-Speech Web App  
Powered by Microsoft Edge Neural TTS

## Features

- 🎤 **Thiha** (ကျား) / **Nilar** (မ) အသံ
- ⚡ Speed 0.8x ~ 2.0x (Default 1.4x)
- 💾 Preference သိမ်းဆည်း (localStorage)
- 🎧 MP3 Download
- 📝 Transcript TXT Download
- ✅ **Chrome / Firefox / Safari / Edge** အားလုံးမှာ အလုပ်လုပ်

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open in browser:

```
http://127.0.0.1:5000
```

## API

### POST `/api/tts`

```json
{
  "text": "မင်္ဂလာပါ",
  "voice": "thiha",
  "speed": 1.4
}
```

Returns: `audio/mpeg` (MP3)

### GET `/api/voices`

Returns available voices and speeds.
