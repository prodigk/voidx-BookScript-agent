# Remotion 영상 파이프라인

## 결정

영상 생성의 최우선 렌더러는 Remotion이다. Python 파이프라인은 출처 검증이 승인된 대본을 renderer-neutral manifest로 변환하고, 로컬 React/TypeScript 프로젝트가 이를 프레임 기반 영상으로 렌더링한다.

```text
approved script_with_sources.md + citations.json
→ scripts/prepare_video.py
→ outputs/<run-id>/video_manifest.json
→ video/src/data/current-video.json
→ Remotion BookVideo Composition
```

검증 상태가 `approved`가 아니거나 invalid citation이 남아 있으면 manifest 생성을 차단한다. 원본 Markdown과 API 키는 영상 프로젝트에 복사하지 않는다.

## manifest 내용

- 실행 ID와 승인 상태
- 1920×1080, FPS, 총 프레임 수
- 안정적인 section ID
- 섹션 시작·종료 초와 프레임
- 내레이션
- 화면 목적과 짧은 화면 문구
- 향후 준비할 자산 힌트
- 직접 인용 원문, 책 제목, 원본 파일과 행 범위
- 결말 참고 도서 목록

섹션은 시간 공백이나 겹침 없이 이어져야 하며 마지막 섹션의 종료 시간이 전체 영상 길이와 일치해야 한다.

## 현재 시각 시스템

- 16:9 1920×1080
- 차분한 야간 네이비 배경과 제한적인 coral 강조색
- 좌우 120px, 상하 100px 안전 영역
- 한 장면에 제목 하나와 화면 문구 최대 2개
- CSS animation 없이 `useCurrentFrame()`과 `interpolate()`만 사용
- 모든 섹션을 premount된 `Sequence`로 구성
- 인용 카드는 검증된 원문 한 구절과 읽기 쉬운 출처만 표시
- 마지막 12초에 참고 도서 전체를 한 번에 표시

## 실행

```bash
uv run python scripts/prepare_video.py --run-id "<approved-run-id>"
cd video
npm install
npm run dev
```

검사와 렌더:

```bash
npm run lint
npm run build
npm run still
npm run render
```

`npm run render`는 현재 음성 없는 모션 그래픽 MP4를 만든다. 실제 제작용 렌더 전에는 내레이션 음성, 문장 단위 자막 시간, 로컬 이미지·영상 자산을 추가하는 후속 단계가 필요하다.

## 후속 작업

1. 내레이션 음성 파일과 실제 길이를 manifest에 연결한다.
2. 음성 기준으로 문장 단위 자막 타이밍을 생성한다.
3. `suggested_assets`를 로컬 검수 자산 목록으로 변환한다.
4. 음성 길이에 맞춰 섹션 프레임을 재계산한다.
5. 전체 MP4를 렌더하고 오디오·자막·인용 카드 싱크를 검수한다.

## 내레이션 음성

현재 영상은 다음 경로의 음성을 자동 감지한다.

```text
video/public/audio/<run-prefix>/narration.mp3
```

`run-prefix`는 실행 ID의 날짜, 시간, 식별자 세 부분이다. 음성이 존재하면 `@remotion/media`의 `Audio`로 재생하고 Mediabunny가 실제 길이를 측정한다. `calculateMetadata`는 측정된 길이를 올림한 프레임 수를 전체 duration으로 사용하고 기존 6개 섹션을 같은 비율로 재배치한다. 인용 카드는 해당 인용문이 섹션 내레이션에서 등장하는 문자 위치를 기준으로 근사 배치한다.

이 방식은 전체 길이와 섹션 수준 싱크를 맞추지만 문장별 발화 시각을 보장하지 않는다. 정확한 자막과 인용 장면 싱크에는 음성 전사 또는 forced alignment 결과가 필요하다.
