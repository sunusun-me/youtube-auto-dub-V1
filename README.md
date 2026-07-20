# youtube-auto-dub (V1)

> English | [中文](README.zh.md)

A local pipeline that automatically generates **bilingual subtitles + Chinese dubbing** for YouTube videos (macOS / Apple Silicon).

Give it a YouTube link, and it runs everything locally: download → speech recognition → translation → speech synthesis → mixing → final render. Fully free / local — no paid APIs required.

## Features

- **One command**: `py <URL>` end-to-end, no manual steps.
- **Bilingual**: keeps the original audio track and overlays Chinese dubbing, with subtitles.
- **Local recognition**: Whisper (faster-whisper) transcription, Apple Silicon supported.
- **Free translation**: Google's unofficial RPC translation channel, concurrent + exponential backoff to avoid rate limits.
- **Neural TTS**: Edge-TTS Microsoft voices, with automatic fallback to the macOS local `say`.
- **Stable mixing**: in-memory audio overlay via pydub + hardware-accelerated render with FFmpeg (`h264_videotoolbox`).

## Requirements

- macOS (Apple Silicon recommended)
- Python 3.10+ (verified on 3.12; 3.9 and below may fail due to `onnxruntime` / `faster-whisper`)
- FFmpeg (`brew install ffmpeg`)

## Installation

```bash
git clone https://github.com/sunusun-me/youtube-auto-dub-V1.git
cd youtube-auto-dub-V1

# Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Apple Silicon users: the `torch` in `requirements.txt` uses the CPU build (Metal acceleration is enabled automatically); no CUDA build needed.

## Usage

The repo ships a one-shot entry point `./py` (works right after clone):

```bash
# One command: Chinese dubbing + Chinese subtitles (source language auto-detected)
./py "https://www.youtube.com/watch?v=<VIDEO_ID>"

# Variants
./py "<URL>" en            # English subtitles + keep original audio (skips dubbing if source is en)
./py "<URL>" cn medium     # 3rd arg picks the Whisper model (tiny/base/small/medium, default small)

# Change the dubbing voice (male)
VOICE=zh-CN-YunjianNeural ./py "<URL>"
```

> Optional: if you want to invoke dubbing from any directory via global commands `py` / `dub` / `python <URL>`, add a shell alias pointing to this directory's `py` yourself. The repo only depends on `./py` and does not require this setup.

You can also call `main.py` directly for custom parameters:

```bash
python main.py "<URL>" --mode both --lang_dub zh-CN --voice yunjian
```

Common options:

| Option | Short | Description |
|--------|-------|-------------|
| `url` | | YouTube video link (required) |
| `--mode` | `-m` | `sub` (subtitles only) / `dub` (dubbing only) / `both` (subtitles + dubbing) |
| `--lang` | `-l` | Target language (applied to both subtitles and dubbing) |
| `--lang_sub` | `-ls` | Override subtitle language (e.g. English subtitles + Chinese dubbing) |
| `--lang_dub` | `-ld` | Override dubbing language |
| `--whisper_model` | `-wm` | Whisper model: `tiny` / `base` / `small` / `medium` |
| `--voice` | `-v` | Voice; accepts aliases `yunjian` (calm male) / `xiaoxiao` (expressive female) / `yunxi` (lively male), full names like `zh-CN-XiaoxiaoNeural`, or system local voices such as `Tingting` |
| `--browser` | `-b` | Extract cookies from a browser: `chrome` / `edge` / `firefox` |

## How It Works

**Pipeline**:

```
YouTube URL → Download → Whisper ASR → Segmentation → Translation → Edge-TTS → pydub Mixing → FFmpeg Render
```

1. **Download** (`src/youtube.py`): yt-dlp extracts the video stream and audio.
2. **Recognition** (`main.py`): Whisper transcribes locally, producing timestamped text.
3. **Segmentation** (`src/media.py`): splits text into natural sentences by silence gaps (max ~10s).
4. **Translation** (`src/googlev4.py`): concurrent translation over the Google RPC channel + exponential backoff.
5. **Synthesis** (`src/tts.py`): Edge-TTS voice mapping, falling back to local `say` on failure.
6. **Mixing** (`src/media.py`): in-memory overlay of original audio and dubbing via pydub.
7. **Render** (`main.py`): FFmpeg hardware-accelerated muxing of audio track + subtitles.

**Project layout**:

```
youtube-auto-dub-V1/
├── py                  # one-shot dubbing entry point
├── main.py             # CLI parsing and pipeline orchestration
├── requirements.txt    # dependency snapshot
├── language_map.json   # language → default voice mapping
└── src/
    ├── models.py       # core data structures
    ├── youtube.py      # yt-dlp download wrapper
    ├── media.py        # segmentation / mixing / rendering
    ├── googlev4.py     # Google RPC translation channel
    ├── tts.py          # Edge-TTS synthesis + local fallback
    └── ui.py           # Rich terminal rendering
```

Runtime outputs: `output/` (final videos), `.cache/` (download cache), `temp/` (temporary segments, auto-cleared after each run). The cache can be freed anytime with `rm -rf .cache/*`.

## Security Notice

> This tool is for **personal learning and technical research only**. Comply with the copyright laws of your region and the terms of service of YouTube / Google / Microsoft. The user bears sole responsibility for any account bans or legal disputes caused by misuse (bulk downloading, redistributing copyrighted content, circumventing platform restrictions).

**Cookies & credentials**

- `cookies.txt` / `.venv/` are ignored by `.gitignore` and **never committed**.
- `cookies.txt` is only used locally by yt-dlp to bypass login / age restrictions; export it from your own browser and never upload it to any public repo or chat tool.
- If a credential file is accidentally committed, **revoke the affected session immediately** (change password / sign out of devices) — leaked tokens remain accessible from old commits even after the file is deleted.
- Never put GitHub PATs, login cookies, or `.env` files into this repo.

**Third-party API risks**

- Translation defaults to Google's unofficial RPC and TTS defaults to Edge-TTS, both unofficial calls that may be rate-limited or changed at any time. For production / long-term use, switch to official APIs (Google Cloud Translation / Azure TTS) or local open-source alternatives, with proper fallback handling.

## License

Based on the open-source project by [@mangodxd](https://github.com/mangodxd), refactored and optimized for Apple Silicon (M4) by **nusun**. This derivative is released under the **MIT** License; see [LICENSE](LICENSE).
