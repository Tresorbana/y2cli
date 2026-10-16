# y2cli

**Download YouTube videos and audio from your terminal — no browser, no ads, no limits.**

Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) with **ffmpeg bundled** (nothing extra to install). Just `pip install` and go.

---

## Install

```bash
pip install y2cli
```

Requires Python 3.10+. Works on Windows, macOS, and Linux.

---

## Quick Start

Run `y2cli` and it will ask you for everything:

```
y2cli
```

You'll be prompted for a YouTube URL, then shown an arrow-key menu to pick your format:

```
? Choose format:
  > MP3 (audio only)
    MP4 1080p
    MP4 720p
    MP4 480p
    MP4 360p
```

That's it. The file saves to `~/Downloads/y2cli/` when done.

---

## Usage

```bash
# Fully interactive (recommended)
y2cli

# Pass a URL, then pick format from the menu
y2cli "https://www.youtube.com/watch?v=VIDEO_ID"

# Skip the menu — download directly
y2cli "https://www.youtube.com/watch?v=VIDEO_ID" --format mp4_720
y2cli "https://www.youtube.com/watch?v=VIDEO_ID" --format mp3

# Save to a custom folder
y2cli "https://..." --format mp4_720 --output ~/Videos

# See what formats are available for a video (JSON)
y2cli "https://..." --info
```

### Format IDs

| ID | Description |
|----|-------------|
| `mp3` | Audio only (192 kbps MP3) |
| `mp4_1080` | Video 1080p |
| `mp4_720` | Video 720p |
| `mp4_480` | Video 480p |
| `mp4_360` | Video 360p |

Available resolutions depend on what the video offers. The interactive menu only shows what's actually available.

---

## Features

- No ffmpeg install needed — it's bundled
- Arrow-key format picker so you never have to remember IDs
- MP3 and MP4 support with automatic merging
- Clean progress display in the terminal
- Saves to `~/Downloads/y2cli/` by default

---

## HTTP Server (for developers)

You can run y2cli as a local HTTP server for use in your own scripts or tools:

```bash
y2cli --serve          # starts on port 7272
y2cli --serve --port 8080
```

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET | `/ping` | — | Health check |
| POST | `/info` | `{"url": "..."}` | Get video info and available formats |
| POST | `/download` | `{"url": "...", "format_id": "mp4_720"}` | Start a download, returns `job_id` |
| GET | `/progress?job_id=...` | — | Poll download progress |

---

## License

MIT — free to use, modify, and distribute.
