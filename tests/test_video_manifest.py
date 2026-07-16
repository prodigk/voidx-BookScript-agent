import json
from pathlib import Path

import pytest

from app.config import ProjectSettings, Settings, VideoSettings
from app.video.manifest import prepare_video_manifest


SCRIPT = """# 테스트 영상

- 예상 길이: 1분
- 영상 렌더러: remotion
- 기준 FPS: 30

## 도입

<!-- REMOTION: section_id=s1 start=0s end=30s fps=30 -->
<!-- VISUAL: 밤의 책상에서 질문을 제시한다. -->
<!-- ON_SCREEN_TEXT: 오늘의 질문 -->
<!-- ASSETS: 어두운 책상 -->

첫 번째 내레이션입니다.

[TYPE:commentary] [PARAGRAPH:s1_p1]

## 결론

<!-- REMOTION: section_id=s2 start=30s end=60s fps=30 -->
<!-- VISUAL: 차분한 인용문과 함께 마무리한다. -->
<!-- ON_SCREEN_TEXT: 나를 잃지 않는 태도 -->
<!-- ASSETS: 천천히 밝아지는 창문 -->

<!-- QUOTE_SCENE: duration=8s -->
<!-- QUOTE_TEXT: 원문 그대로의 문장 -->
<!-- QUOTE_SOURCE: 테스트 책 | 책.md:10-12 -->

원문 그대로의 문장

[TYPE:quotation] [PARAGRAPH:s2_p1] [BOOK:book_1] [SOURCE:ev_1] [CHUNK:chunk_1]

이 영상은 『테스트 책』의 내용을 바탕으로 구성되었습니다.

[TYPE:commentary]
"""


def _settings(tmp_path: Path) -> tuple[Settings, str, Path]:
    run_id = "approved_run"
    output = tmp_path / "outputs"
    run = output / run_id
    run.mkdir(parents=True)
    (run / "script_with_sources.md").write_text(SCRIPT, encoding="utf-8")
    video = tmp_path / "video"
    audio = video / "public/audio/approved_run/narration.mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"test-audio")
    settings = Settings(
        project=ProjectSettings(output_path=output),
        video=VideoSettings(project_path=video, fps=30, width=1920, height=1080),
    )
    return settings, run_id, run


def test_prepares_contiguous_manifest_and_syncs_remotion_input(tmp_path: Path) -> None:
    settings, run_id, run = _settings(tmp_path)
    (run / "citations.json").write_text(
        json.dumps({"status": "approved", "invalid_count": 0}), encoding="utf-8",
    )
    manifest = prepare_video_manifest(settings, run_id)
    assert manifest.duration_frames == 1800
    assert [scene.start_frame for scene in manifest.scenes] == [0, 900]
    assert manifest.scenes[1].quote is not None
    assert manifest.scenes[1].quote.text == "원문 그대로의 문장"
    assert manifest.scenes[1].quote.display_source == "『테스트 책』 · 원문 10–12행"
    assert manifest.reference_books == ["테스트 책"]
    assert manifest.audio is not None
    assert manifest.audio.src == "audio/approved_run/narration.mp3"
    assert (run / "video_manifest.json").is_file()
    assert (settings.video.project_path / "src/data/current-video.json").is_file()


def test_blocks_video_preparation_for_unapproved_script(tmp_path: Path) -> None:
    settings, run_id, run = _settings(tmp_path)
    (run / "citations.json").write_text(
        json.dumps({"status": "needs_revision", "invalid_count": 1}), encoding="utf-8",
    )
    with pytest.raises(ValueError, match="blocked"):
        prepare_video_manifest(settings, run_id)
