# Video Clip Pipeline — RESOLUTE Local

Automatically discovers, downloads, transcribes, and timestamp-links city council
meeting recordings so citizens can jump directly to any agenda item in the video.

## How it works

1. **Discovery** — `yt-dlp` polls the broadcaster's Vimeo account for new recordings
   matching "City Council" in the title.
2. **Download** — audio-only (WAV, 16kHz mono) via `yt-dlp` + `ffmpeg` post-process.
3. **Transcription** — `whisper-cli` (whisper.cpp `ggml-small.en` model) produces
   a timestamped SRT transcript.
4. **Agenda matching** — a local LLM (Qwen on `localhost:1235`) maps each transcript
   timestamp to the agenda sections from the city's agenda center.
5. **Output** — per-meeting clip metadata (section → {start_sec, end_sec, Vimeo URL})
   written to `fxbg-video-clips.json`.
6. **Publish** — `publish-fredericksburg.py` merges clip metadata into
   `data/fredericksburg.json`; the city page JS renders "▶ 0:23:15" timestamp
   links inline with agenda items.

## Fredericksburg, VA setup

| What | Value |
|------|-------|
| Broadcaster | Regional WebTV (AMS VA) |
| Platform | Vimeo |
| Vimeo user | `user137718836` |
| Vimeo live event | `event/898581` (always shows latest recording) |
| Filter term | title contains "Fredericksburg" AND "Council" (not "School") |
| Runs | Daily 11am + immediately after post-meeting trigger (9:30pm) |

The live event embed (`https://vimeo.com/event/898581/embed/interaction`) is shown
on the city page's "Next Meeting" card — it's active during streams and shows the
latest recording when idle.

## Requirements

```bash
brew install whisper-cpp yt-dlp ffmpeg python3
```

Whisper model (small, English — ~150MB):

```bash
mkdir -p ~/.openclaw/whisper_models
curl -L https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin \
     -o ~/.openclaw/whisper_models/ggml-small.en.bin
```

A local LLM server must be running on `localhost:1235` (OpenAI-compatible).
Any model ≥7B parameters works; Qwen3.6 35B (or similar) gives best agenda matching.

## Running manually

```bash
# Process the latest recording automatically (checks for new since last run)
python3 ~/Scripts/fxbg-video-pipeline.py

# Process a specific Vimeo video ID (e.g., after a meeting)
python3 ~/Scripts/fxbg-video-pipeline.py --force-id 1195787791

# Dry run — shows what would be processed without downloading
python3 ~/Scripts/fxbg-video-pipeline.py --dry-run

# Skip re-downloading if WAV is already cached in /tmp/fxbg-video-work/
python3 ~/Scripts/fxbg-video-pipeline.py --force-id 1195787791 --skip-download
```

## Output files

| File | Description |
|------|-------------|
| `~/.openclaw/shared-memory/context/fxbg-video-clips.json` | Per-meeting clip metadata keyed by date |
| `~/.openclaw/shared-memory/context/fxbg-video-state.json` | Processed Vimeo IDs (prevents re-processing) |
| `/tmp/fxbg-video-work/<id>.wav` | Cached audio (safe to delete to free disk) |
| `/tmp/fxbg-video-work/<id>.srt` | Cached whisper transcript |
| `~/.openclaw/logs/fxbg-video-pipeline.log` | Run log |

## Adapting for your city

1. Find your city's meeting broadcaster. Common platforms: YouTube, Vimeo, Granicus,
   Swagit, Facebook Live. `yt-dlp` supports all of these.

2. In `fxbg-video-pipeline.py`, update:
   - `VIMEO_USER` → your broadcaster's account ID
   - `find_fxbg_council_videos()` → adjust title filter for your city name

3. If your city uses YouTube (most do): replace the Vimeo URL with:
   ```
   https://www.youtube.com/channel/<CHANNEL_ID>/videos
   ```
   yt-dlp handles YouTube channels identically.

4. For the live embed in the city page, replace the Vimeo event iframe with:
   - **YouTube Live**: `https://www.youtube.com/embed/live_stream?channel=<ID>`
   - **Granicus**: embed URL from the city's Granicus page
   - **Facebook Live**: `https://www.facebook.com/plugins/video.php?href=<page_url>`

5. The agenda matching (Qwen) is city-agnostic — it reads whatever sections
   `publish-<city>.py` produced. No changes needed.

## Performance

On an Apple M5 Max (128GB RAM):
- Audio download: ~3 min for a 90-min meeting
- Whisper transcription (small.en): ~3-4 min for 90 min of audio
- Qwen agenda matching: ~30 sec

Total: **~7-8 minutes** from new Vimeo video → timestamp links live on the page.

## Why Vimeo, not YouTube?

Fredericksburg's broadcaster (Regional WebTV) used YouTube through 2019, then
switched to Vimeo for live streaming. The switch was discovered by extracting
iframe sources from the Wix-hosted `regionalwebtv.com/fredcc` page — the embed
pointed to `vimeo.com/event/898581`.

When adapting this for another city: check the broadcaster's streaming page
source to find the actual embed provider. Many cities use YouTube but some
use Vimeo, Granicus, or Facebook Live.
