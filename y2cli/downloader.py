import os
import yt_dlp
import imageio_ffmpeg


def get_ffmpeg() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def fetch_info(url: str) -> dict:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def build_formats(info: dict) -> list[dict]:
    choices = [{"id": "mp3", "label": "MP3 (audio only)", "type": "audio",
                "format": "bestaudio/best"}]
    heights = sorted(
        {f.get("height") for f in info.get("formats", [])
         if f.get("height") and f.get("vcodec", "none") != "none"},
        reverse=True,
    )
    for h in heights:
        choices.append({
            "id": f"mp4_{h}",
            "label": f"MP4 {h}p",
            "type": "video",
            "format": (
                f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
                f"/bestvideo[height<={h}]+bestaudio/best[height<={h}]"
            ),
        })
    if len(choices) == 1:
        choices.append({"id": "mp4_best", "label": "MP4 (best quality)",
                        "type": "video", "format": "bestvideo+bestaudio/best"})
    return choices


def download(url: str, fmt: dict, output_dir: str, progress_hook=None) -> None:
    os.makedirs(output_dir, exist_ok=True)
    opts = {
        "format": fmt["format"],
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": get_ffmpeg(),
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    if fmt["type"] == "audio":
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
