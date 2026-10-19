"""
y2cli — CLI entry point.

Modes:
  y2cli                          interactive (prompts for URL + format)
  y2cli <URL>                    interactive format picker
  y2cli <URL> --format mp4_720   direct download, no prompts
  y2cli <URL> --info             print video info as JSON
  y2cli <URL> --format mp4_720 --json   progress as JSON lines (for editors/extensions)
  y2cli --serve [--port 7272]    start local HTTP server for browser/VS Code extensions
"""

import argparse
import json
import os
import sys

import sys
from rich.console import Console
from rich.panel import Panel

from y2cli import __version__
from y2cli.downloader import fetch_info_auto, build_formats, download, _is_bot_error, BROWSERS

# Only emit color codes when connected to a real terminal
console = Console(force_terminal=sys.stdout.isatty())
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "y2cli")


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_rich_hook():
    def hook(d):
        if d["status"] == "downloading":
            info = d.get("info_dict", {})
            is_audio = info.get("vcodec", "none") == "none"
            label = "[yellow]Audio[/]" if is_audio else "[cyan]Video[/]"
            pct   = d.get("_percent_str", "?").strip()
            speed = d.get("_speed_str",   "?").strip()
            eta   = d.get("_eta_str",     "?").strip()
            console.print(f"  {label} {pct}  speed: {speed}  eta: {eta}      ", end="\r")
        elif d["status"] == "finished":
            info = d.get("info_dict", {})
            is_audio = info.get("vcodec", "none") == "none"
            label = "Audio" if is_audio else "Video"
            console.print(f"\n[green]✓ {label} downloaded[/]")
    return hook


def _make_json_hook():
    def hook(d):
        if d["status"] == "downloading":
            msg = {
                "type":    "progress",
                "percent": d.get("_percent_str", "").strip(),
                "speed":   d.get("_speed_str",   "").strip(),
                "eta":     d.get("_eta_str",      "").strip(),
            }
            print(json.dumps(msg), flush=True)
        elif d["status"] == "finished":
            filename = d.get("filename", "")
            print(json.dumps({"type": "done", "filename": os.path.basename(filename),
                               "path": filename}), flush=True)
    return hook


def _pick_format_interactive(info: dict, choices: list[dict]) -> dict:
    import questionary
    from questionary import Style

    title    = info.get("title", "Unknown")
    uploader = info.get("uploader", "?")
    duration = info.get("duration_string") or str(info.get("duration", "?"))

    console.print(Panel(
        f"[bold cyan]{title}[/]\n[dim]Channel:[/] {uploader}   [dim]Duration:[/] {duration}",
        title="[bold green]y2cli[/]",
        border_style="green",
    ))

    style = Style([
        ("qmark",        "fg:#10b981 bold"),
        ("question",     "bold"),
        ("answer",       "fg:#10b981 bold"),
        ("pointer",      "fg:#10b981 bold"),
        ("highlighted",  "fg:#10b981 bold"),
        ("selected",     "fg:#10b981"),
    ])

    label = questionary.select(
        "Choose format:",
        choices=[c["label"] for c in choices],
        style=style,
        use_shortcuts=False,
    ).ask()

    if label is None:
        console.print("[red]Cancelled.[/]")
        sys.exit(0)

    return next(c for c in choices if c["label"] == label)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(prog="y2cli", description="Y2Mate-style offline downloader")
    parser.add_argument("url", nargs="?", help="YouTube (or other) URL")
    parser.add_argument("--format", "-f", dest="fmt_id", help="Format id, e.g. mp3 / mp4_720")
    parser.add_argument("--output", "-o", default=DEFAULT_DIR, help="Output directory")
    parser.add_argument("--info",   action="store_true", help="Print video info as JSON and exit")
    parser.add_argument("--json",   action="store_true", help="Emit progress as JSON lines")
    parser.add_argument("--serve",  action="store_true", help="Start local HTTP server")
    parser.add_argument("--port",   type=int, default=7272)
    parser.add_argument("--version", action="version", version=f"y2cli {__version__}")
    args = parser.parse_args()

    # ── server mode ──────────────────────────────────────────────────────────
    if args.serve:
        from y2cli.server import run_server
        run_server(port=args.port)
        return

    # ── get URL ──────────────────────────────────────────────────────────────
    url = args.url
    if not url:
        if args.json:
            print(json.dumps({"type": "error", "message": "No URL provided"}), flush=True)
            sys.exit(1)
        console.print(Panel("[bold green]y2cli[/] v" + __version__, border_style="dim green"))
        url = Prompt.ask("[bold]Paste YouTube URL[/]").strip()
    if not url:
        console.print("[red]No URL provided.[/]")
        sys.exit(1)

    # ── fetch info ───────────────────────────────────────────────────────────
    if not args.json:
        console.print("[dim]Fetching video info…[/]")
    try:
        import yt_dlp
        info, browser = fetch_info_auto(url)
        if browser and not args.json:
            console.print(f"[dim]Using {browser} cookies to bypass YouTube verification.[/]")
    except yt_dlp.utils.DownloadError as e:
        if args.json:
            print(json.dumps({"type": "error", "message": str(e)}), flush=True)
        else:
            console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    # ── --info mode ───────────────────────────────────────────────────────────
    if args.info:
        choices = build_formats(info)
        out = {
            "title":    info.get("title", ""),
            "uploader": info.get("uploader", ""),
            "duration": info.get("duration_string") or str(info.get("duration", "")),
            "thumbnail": info.get("thumbnail", ""),
            "formats":  [{"id": c["id"], "label": c["label"], "type": c["type"]} for c in choices],
        }
        print(json.dumps(out))
        return

    # ── pick format ───────────────────────────────────────────────────────────
    choices = build_formats(info)
    if args.fmt_id:
        matched = next((c for c in choices if c["id"] == args.fmt_id), None)
        if not matched:
            msg = f"Unknown format '{args.fmt_id}'. Available: {[c['id'] for c in choices]}"
            if args.json:
                print(json.dumps({"type": "error", "message": msg}), flush=True)
            else:
                console.print(f"[red]{msg}[/]")
            sys.exit(1)
        selected = matched
    else:
        selected = _pick_format_interactive(info, choices)

    # ── download ──────────────────────────────────────────────────────────────
    hook = _make_json_hook() if args.json else _make_rich_hook()

    if not args.json:
        console.print(f"\n[bold]Downloading:[/] [cyan]{selected['label']}[/] → [dim]{args.output}[/]\n")

    try:
        import yt_dlp
        download(url, selected, args.output, progress_hook=hook, browser=browser)
    except yt_dlp.utils.DownloadError as e:
        if _is_bot_error(e) and not browser:
            if not args.json:
                console.print("[yellow]YouTube blocked the request. Retrying with browser cookies…[/]")
            for b in BROWSERS:
                try:
                    download(url, selected, args.output, progress_hook=hook, browser=b)
                    break
                except Exception:
                    continue
            else:
                console.print("[red]Download failed:[/] YouTube is blocking all requests. Open YouTube in your browser and try again.")
                sys.exit(1)
        else:
            if args.json:
                print(json.dumps({"type": "error", "message": str(e)}), flush=True)
            else:
                console.print(f"[red]Download failed:[/] {e}")
            sys.exit(1)

    if not args.json:
        console.print(f"\n[bold green]Saved to:[/] {args.output}")
