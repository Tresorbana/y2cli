# y2cli

Offline YouTube downloader CLI — works exactly like Y2Mate but runs on your machine with no browser needed. Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp) with **ffmpeg bundled** via [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) (no separate ffmpeg install required).

## Features

- Download YouTube videos as MP4 (1080p, 720p, 480p, 360p, and more)
- Download audio as MP3
- Interactive format picker (like Y2Mate's UI, in the terminal)
- Built-in ffmpeg — no manual setup
- Local HTTP server mode for the VS Code and browser extensions
- JSON output mode for programmatic use

## Install

```bash
pip install y2cli
```

Or install from source:

```bash
git clone https://github.com/YOUR_USERNAME/y2cli
cd y2cli
pip install -e .
```

## Usage

```bash
# Interactive — prompts for URL and format
y2cli

# Pass URL directly, pick format interactively
y2cli "https://www.youtube.com/watch?v=VIDEO_ID"

# Direct download, no prompts
y2cli "https://..." --format mp4_720
y2cli "https://..." --format mp3

# Available format IDs
# mp3, mp4_1080, mp4_720, mp4_480, mp4_360  (depends on video)

# Custom output directory
y2cli "https://..." --format mp4_720 --output "C:\Users\You\Videos"

# Get video info as JSON (used by extensions)
y2cli "https://..." --info

# Start local HTTP server (for VS Code / browser extensions)
y2cli --serve
y2cli --serve --port 8080
```

Downloads save to `~/Downloads/y2cli/` by default.

## HTTP Server API

When running `y2cli --serve` (default port `7272`):

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET | `/ping` | — | Health check |
| POST | `/info` | `{"url": "..."}` | Get video info + formats |
| POST | `/download` | `{"url": "...", "format_id": "mp4_720"}` | Start download, returns `job_id` |
| GET | `/progress?job_id=...` | — | Poll download progress |

## Related Projects

- [y2cli-vscode](https://github.com/YOUR_USERNAME/y2cli-vscode) — VS Code extension
- [y2cli-browser](https://github.com/YOUR_USERNAME/y2cli-browser) — Chrome/Firefox browser extension

## License

MIT
