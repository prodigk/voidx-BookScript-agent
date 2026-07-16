"""Convert an approved sourced script into a strict Remotion video manifest."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.agents.phase5 import resolve_run_dir
from app.config import Settings
from app.schemas.video import VideoAudio, VideoManifest, VideoQuote, VideoScene

SECTION_RE = re.compile(r"(?m)^## (?P<title>.+)$")
REMOTION_RE = re.compile(
    r"<!-- REMOTION: section_id=(?P<id>[a-z0-9_-]+) start=(?P<start>\d+)s "
    r"end=(?P<end>\d+)s fps=(?P<fps>\d+) -->"
)


def _comment(block: str, name: str) -> str | None:
    match = re.search(rf"<!-- {name}: (.*?) -->", block)
    return match.group(1).strip() if match else None


def _section_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(SECTION_RE.finditer(text))
    return [
        (match.group("title").strip(), text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)])
        for index, match in enumerate(matches)
    ]


def _narration(block: str) -> str:
    lines = []
    for line in block.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("<!--") or re.fullmatch(r"(?:\[[A-Z]+:[^\]]*\]\s*)+", stripped):
            continue
        lines.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _quote_display_source(source: str) -> str:
    title, _, location = source.partition("|")
    line_match = re.search(r":(\d+)-(\d+)$", location.strip())
    if line_match:
        return f"『{title.strip()}』 · 원문 {line_match.group(1)}–{line_match.group(2)}행"
    return f"『{title.strip()}』"


def _audio_asset(settings: Settings, run_id: str) -> VideoAudio | None:
    run_prefix = "_".join(run_id.split("_")[:3])
    relative = Path("audio") / run_prefix / settings.video.audio_filename
    source = settings.video.project_path / "public" / relative
    return VideoAudio(src=relative.as_posix()) if source.is_file() else None


def prepare_video_manifest(settings: Settings, run_id: str, *, sync_project: bool = True) -> VideoManifest:
    """Create video_manifest.json only from an approved, source-linked script run."""
    run_dir = resolve_run_dir(settings.project.output_path, run_id)
    sourced_path = run_dir / "script_with_sources.md"
    validation_path = run_dir / "citations.json"
    if not sourced_path.is_file() or not validation_path.is_file():
        raise FileNotFoundError("Approved script and citation artifacts are required")
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if validation.get("status") != "approved" or validation.get("invalid_count") != 0:
        raise ValueError("Video preparation is blocked until citation validation is approved")

    sourced = sourced_path.read_text(encoding="utf-8")
    title_match = re.match(r"^# ([^\n]+)", sourced)
    if title_match is None:
        raise ValueError("Sourced script title is missing")
    scenes: list[VideoScene] = []
    fps: int | None = None
    for title, block in _section_blocks(sourced):
        timing = REMOTION_RE.search(block)
        if timing is None:
            raise ValueError(f"Remotion timing marker is missing: {title}")
        scene_fps = int(timing.group("fps"))
        if fps is not None and scene_fps != fps:
            raise ValueError("All scenes must use the same FPS")
        fps = scene_fps
        start, end = int(timing.group("start")), int(timing.group("end"))
        quote_text = _comment(block, "QUOTE_TEXT")
        quote_duration = _comment(block, "QUOTE_SCENE")
        quote_source = _comment(block, "QUOTE_SOURCE")
        quote = None
        if quote_text or quote_duration or quote_source:
            if not quote_text or not quote_duration or not quote_source:
                raise ValueError(f"Incomplete quote scene markers: {title}")
            duration_match = re.fullmatch(r"duration=(\d+)s", quote_duration)
            if duration_match is None:
                raise ValueError(f"Invalid quote duration marker: {title}")
            quote = VideoQuote(
                text=quote_text,
                source=quote_source,
                display_source=_quote_display_source(quote_source),
                duration_seconds=int(duration_match.group(1)),
            )
        visual = _comment(block, "VISUAL")
        if visual is None:
            raise ValueError(f"Visual intent is missing: {title}")
        scenes.append(VideoScene(
            section_id=timing.group("id"), title=title,
            start_seconds=start, end_seconds=end,
            start_frame=start * scene_fps, duration_frames=(end - start) * scene_fps,
            narration=_narration(block), visual_intent=visual,
            on_screen_text=[item.strip() for item in (_comment(block, "ON_SCREEN_TEXT") or "").split("|") if item.strip()],
            suggested_assets=[item.strip() for item in (_comment(block, "ASSETS") or "").split("|") if item.strip()],
            quote=quote,
        ))
    if fps is None:
        raise ValueError("No Remotion scenes found")
    reference_books = list(dict.fromkeys(re.findall(r"『([^』]+)』", scenes[-1].narration)))
    if not reference_books:
        raise ValueError("Final book attribution is missing from the approved script")
    manifest = VideoManifest(
        run_id=run_id,
        title=title_match.group(1).strip(),
        fps=fps,
        width=settings.video.width,
        height=settings.video.height,
        duration_seconds=scenes[-1].end_seconds,
        duration_frames=scenes[-1].end_seconds * fps,
        source_script=(run_dir / "script_with_sources.md").as_posix(),
        audio=_audio_asset(settings, run_id),
        reference_books=reference_books,
        scenes=scenes,
    )
    payload = manifest.model_dump_json(indent=2)
    (run_dir / "video_manifest.json").write_text(payload + "\n", encoding="utf-8")
    if sync_project:
        target = settings.video.project_path / "src" / "data" / "current-video.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + "\n", encoding="utf-8")
    return manifest
