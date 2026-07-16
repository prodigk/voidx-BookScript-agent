# BookVideo Remotion renderer

승인된 YouTube Book Script Agent 실행을 렌더링하는 로컬 Remotion 프로젝트입니다.

먼저 저장소 루트에서 현재 입력을 준비합니다.

```bash
uv run python scripts/prepare_video.py --run-id "<approved-run-id>"
```

그다음 영상 프로젝트를 실행합니다.

```bash
cd video
npm install
npm run dev
```

검사 및 렌더 명령:

```bash
npm run lint
npm run build
npm run still
npm run render
```

- Composition ID: `BookVideo`
- 기본 크기: 1920×1080
- 기본 FPS: 30
- 입력: `src/data/current-video.json`
- 출력: `out/book-video.mp4`

현재는 내레이션 음성을 지원하는 편집형 모션 그래픽 단계입니다. `public/`에 로컬 자산을 추가할 때는 `staticFile()`로만 참조하고 원본 Markdown 또는 비밀 키를 복사하지 않습니다.

내레이션 파일은 `public/audio/<run-prefix>/narration.mp3`에 둡니다. manifest 준비 명령이 파일을 자동 감지하며 Remotion은 실제 음성 길이에 맞춰 전체 프레임을 계산합니다. 문장 단위 자막 싱크는 아직 포함하지 않습니다.
