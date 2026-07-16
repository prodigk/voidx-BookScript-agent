"""Prepare an approved script run for the local Remotion project."""

import argparse

from app.config import load_settings
from app.video.manifest import prepare_video_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="승인된 대본을 Remotion video manifest로 변환")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--no-sync", action="store_true", help="video/src/data 복사를 생략")
    args = parser.parse_args()
    settings = load_settings()
    manifest = prepare_video_manifest(settings, args.run_id, sync_project=not args.no_sync)
    print(f"scenes={len(manifest.scenes)}")
    print(f"frames={manifest.duration_frames}")
    print(settings.project.output_path / args.run_id / "video_manifest.json")


if __name__ == "__main__":
    main()
