"""Continuously synchronize Markdown changes into the local index."""

import argparse

from app.config import load_settings
from app.storage.watcher import watch_index
from app.utils.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown 라이브러리 자동 증분 인덱싱")
    parser.add_argument("--interval", type=float, default=None, help="변경 확인 주기(초)")
    parser.add_argument("--embeddings", action="store_true", help="변경 청크 임베딩 자동 생성(API 비용 발생)")
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.logging.level)
    interval = args.interval or settings.indexing.watch_interval_seconds
    print(f"Watching {settings.project.library_path} every {interval:g}s (종료: Ctrl+C)")
    try:
        watch_index(settings, interval, sync_embeddings=args.embeddings)
    except KeyboardInterrupt:
        print("Index watcher stopped.")


if __name__ == "__main__":
    main()
