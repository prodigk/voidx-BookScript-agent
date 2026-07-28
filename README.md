# YouTube Book Script Agent

로컬 Markdown 도서 노트를 분석해 근거 기반 한국어 YouTube 리서치와 대본을 만드는 로컬 우선 프로젝트입니다. 인문학·철학·심리학을 핵심 편집 범위로 하며 커리어·생산성·조직관리·성과 중심 관점은 새 실행에서 기본 제외합니다. 현재 Phase 0~7.6 파이프라인과 Phase 8의 FastAPI 연구·구성안·대본·검증 작업 API, Next.js 단계별 검토 UI가 구현되어 있습니다.

## 요구 사항

- Python 3.12 이상
- [uv](https://docs.astral.sh/uv/)
- Node.js 20.9 이상과 npm

## 설치

```bash
uv sync
cp .env.example .env
cd frontend && npm install
```

`library/` 아래에 Markdown 파일을 자유롭게 중첩해 둡니다. 한글 파일명과 UTF-8 한글 본문을 지원하며, 원본 파일은 읽기만 합니다.

권장 frontmatter:

```yaml
---
title: 미움받을 용기
author: 기시미 이치로
category: [심리, 자기계발]
tags: [아들러, 인정 욕구]
---
```

## 설정과 환경 변수

기본 설정은 `config/default.yaml`에 있습니다. 다음 환경 변수가 YAML 값을 덮어씁니다.

- `CONFIG_PATH`
- `LIBRARY_PATH`
- `OUTPUT_PATH`
- `DATABASE_PATH`
- `METADATA_PATH`
- `AUDIT_REPORT_PATH`
- `LOG_LEVEL`
- `INDEX_WATCH_INTERVAL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `SCRIPT_MAX_OUTPUT_TOKENS`
- `VIDEO_RENDERER` (기본값 및 최우선 렌더러: `remotion`)
- `VIDEO_WIDTH` (기본값: `1920`)
- `VIDEO_HEIGHT` (기본값: `1080`)
- `VIDEO_PROJECT_PATH` (기본값: `video`)
- `VIDEO_AUDIO_FILENAME` (기본값: `narration.mp3`)
- `INSIGHTS_PATH`
- `INSIGHT_PROFILE` (기본값: `잠들기전 교양이`)
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSIONS`
- `BACKEND_HOST` (기본값: `127.0.0.1`)
- `BACKEND_PORT` (기본값: `8000`)
- `BACKEND_MAX_CONCURRENT_JOBS` (기본값: `1`, 동시에 실행할 연구 작업 수)
- `ALLOWED_ORIGINS` (쉼표로 구분한 허용 frontend origin)
- `LOCAL_API_TOKEN` (터널 연결 시 로컬 FastAPI 요청 검증 토큰)
- `NEXT_PUBLIC_API_BASE_URL` (브라우저가 사용하는 API 주소, production은 `/api/local`)
- `LOCAL_BACKEND_URL` (Vercel 서버 프록시가 호출하는 ngrok HTTPS 주소)
- `LOCAL_BACKEND_TOKEN` (Vercel 서버 전용 로컬 API 토큰, 브라우저 비노출)

경로는 실행 디렉터리를 기준으로 한 상대 경로 또는 절대 경로를 사용할 수 있습니다.

## 사용법

라이브러리 진단:

```bash
uv run python scripts/audit_library.py
```

또는 CLI로 실행:

```bash
uv run python -m app.cli audit-library
uv run python -m app.cli --help
```

SQLite 파일 초기화(Phase 0):

```bash
uv run python -m app.cli init-db
```

진단 결과:

- `reports/library_audit.md`: 파싱 성공/실패, 메타데이터 성공률, 문서·heading·패턴 통계
- `metadata/books.yaml`: 안정적인 ID, 출처 상대 경로, 메타데이터, heading과 content hash

기존 결과 파일은 같은 경로에 갱신됩니다. 원본 `library/` 파일은 변경하지 않습니다.

## 인덱스 생성과 검색

`config/default.yaml`에서 청크 크기를 조정할 수 있습니다.

```yaml
chunking:
  min_chars: 200
  target_chars: 800
  max_chars: 1500
  overlap_chars: 150
```

문서 heading 경로와 문단을 우선하여 청크를 만들고 원본 상대 경로, 실제 행 범위, content hash를 보존합니다. 기본 실행은 content hash 기반 증분 인덱싱입니다.

```bash
uv run python scripts/build_index.py
uv run python scripts/inspect_search.py --query "인정 욕구" --limit 10
```

같은 기능을 CLI로도 사용할 수 있습니다.

```bash
uv run python -m app.cli build-index
uv run python -m app.cli build-index --full
uv run python -m app.cli search --query "인정 욕구" --limit 10
```

검색 결과에는 FTS5 점수, 책 제목·저자, source file, heading 경로, 원본 행 범위와 일치 내용이 표시됩니다. 변경되지 않은 문서는 건너뛰고, 변경된 문서는 해당 책의 청크와 FTS 행을 교체하며, 삭제된 원본의 인덱스도 제거합니다.

Markdown 변경을 계속 자동 반영하려면 watcher를 실행한 상태로 둡니다.

```bash
uv run python scripts/watch_index.py
# 또는 확인 주기 지정
uv run python scripts/watch_index.py --interval 5
```

CLI 명령도 동일하게 동작합니다.

```bash
uv run python -m app.cli watch-index --interval 5
```

watcher는 시작할 때 한 번 증분 동기화한 뒤 기본 10초마다 파일 경로, 수정 시각, 크기를 확인합니다. 변화가 있을 때만 content hash 기반 인덱싱을 실행합니다. 새 `.md`는 추가하고, 수정된 본문이나 frontmatter는 책·청크·FTS 행을 교체하며, 삭제된 `.md`의 인덱스는 제거합니다. 종료는 `Ctrl+C`입니다. 원본 파일은 읽기만 합니다.

의미 검색 벡터까지 계속 자동 반영하려면 API 비용 발생을 명시적으로 허용하는 옵션을 사용합니다.

```bash
uv run python scripts/watch_index.py --embeddings
```

현재 FTS5 기준선을 반복 측정하려면 다음을 실행합니다.

```bash
uv run python scripts/evaluate_retrieval.py
```

평가 데이터는 `data/evaluations/keyword_baseline.yaml`, 결과는 `reports/retrieval_baseline.md`에 저장됩니다. 초기 10개 주제와 기대 도서는 자동 평가를 위한 초안이므로 사용자가 관련성 정답을 검토한 뒤 `needs_review: false`로 확정해야 합니다.

## 임베딩과 하이브리드 검색

`.env`에 API 키와 모델을 설정합니다. API에는 전체 라이브러리가 아니라 인덱싱된 청크 배치만 전송됩니다.

```dotenv
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

누락되거나 변경된 청크의 임베딩만 생성합니다.

```bash
uv run python scripts/build_embeddings.py
uv run python -m app.cli build-embeddings
```

모델 또는 차원을 변경했다면 해당 설정의 별도 캐시가 생성됩니다. 현재 모델 캐시를 강제로 다시 만들려면 다음을 사용합니다.

```bash
uv run python -m app.cli build-embeddings --full
```

의미 검색 및 하이브리드 검색:

```bash
uv run python -m app.cli semantic-search --query "타인의 평가와 인정 욕구" --limit 10
uv run python scripts/inspect_hybrid_search.py --query "타인의 평가와 인정 욕구" --limit 10
uv run python -m app.cli hybrid-search --query "타인의 평가와 인정 욕구" --limit 10
```

하이브리드 결과는 최종 점수와 함께 keyword, semantic, metadata, diversity 점수를 모두 표시합니다. 가중치와 책별 최대 청크 수는 `config/retrieval.yaml`에서 조절합니다.

키워드 기준선과 하이브리드 기준선 비교:

```bash
uv run python scripts/evaluate_hybrid_retrieval.py
```

## Phase 4 도서 리서치

`.env`에 Responses API 모델을 설정합니다.

```dotenv
OPENAI_MODEL=gpt-5.6-luna
```

```bash
uv run python scripts/run_research.py \
  --topic "왜 우리는 타인의 평가를 지나치게 의식하는가" \
  --duration 12 --books 3 --tone "사색적" --audience "일반 성인" \
  --lens "철학" --lens "심리학" \
  --emotional-effect "위로" --emotional-effect "위안" \
  --exclude-lens "투자"
```

CLI에서는 `uv run python -m app.cli research --topic "주제" --books 3`으로 실행합니다. `--lens`, `--emotional-effect`, `--exclude-lens`는 주제별로 반복 지정할 수 있습니다. 모든 요청에는 커리어·생산성·조직관리·성과 중심 제외 정책이 적용되며, 검색 후보 20권을 인문·철학·심리학 편집 방향과 정서 적합성으로 심사한 뒤 최종 후보 10권을 확정합니다. 처리 순서는 `주제 분석 → 검색어 확장 → 하이브리드 검색 → 책 단위 랭킹 → 편집 적합성 심사 → 근거 큐레이션 → 최종 도서 선택`입니다. 검색된 제한 청크만 Responses API에 전달하며, 허용되지 않은 book ID와 chunk ID는 제거합니다. 근거가 부족하면 `insufficient_evidence`로 종료합니다.

각 실행은 `outputs/<run-id>/`에 `input.json`, `topic_analysis.json`, `search_results.json`, `candidate_screening.json`, `candidate_books.json`, `evidence.json`, `selected_books.json`, `research.md`로 저장되며 이전 실행을 덮어쓰지 않습니다. 심사 파일에는 포함 여부, 주제·편집·정서 점수와 제외 사유가 기록됩니다.

## Phase 5 내러티브와 영상 구성안

Phase 4가 완료된 실행 ID를 지정해 근거 기반 내러티브와 제목 후보, 영상 구성안을 생성합니다.

```bash
uv run python scripts/generate_outline.py \
  --run-id "20260713_153812_717813_왜-우리는-타인의-평가를-지나치게-의식하는가"
```

CLI에서는 `uv run python -m app.cli generate-outline --run-id "<run-id>"`을 사용할 수 있습니다. 생성기는 선정된 책과 해당 책의 제한된 근거만 모델에 전달합니다. 모든 도서·근거 ID를 검증하고, 각 섹션 시간을 입력한 영상 길이에 맞춘 뒤 `outputs/<run-id>/narrative.json`과 `outline.md`를 추가합니다. 기존 파일은 덮어쓰지 않습니다.

## Phase 6 출처 연결 대본

Phase 5가 완료된 실행 ID로 내레이션 대본을 생성합니다.

```bash
uv run python scripts/generate_script.py \
  --run-id "20260713_153812_717813_왜-우리는-타인의-평가를-지나치게-의식하는가"
```

CLI에서는 `uv run python -m app.cli generate-script --run-id "<run-id>"`을 사용할 수 있습니다.

기존 대본을 보존하고 새 편집 방향으로 다시 생성하려면 `--revision`을 사용합니다.

```bash
uv run python scripts/generate_script.py --run-id "<run-id>" --revision
```

- `script_with_sources.md`: 문단 유형, 책·근거·청크 ID와 Remotion 장면 타임코드를 포함한 내부 검증용 대본
- `script.md`: 출처와 렌더링 마커를 제거한 내레이션용 대본

대본 생성에는 구성안에 실제로 연결된 source chunk만 전달합니다. 본문에서는 책 제목과 저자를 말하지 않고, 결말 마지막에 참고 도서 전체를 한 번에 소개합니다. 원문과 정확히 일치하는 짧은 인용 화면은 최대 2개만 허용하며 책 제목과 원본 위치는 화면 출처로 표시합니다. 모델이 인용 장면을 누락하면 로컬 원문 대조를 통과한 문장 하나만 결정적으로 보완하며, 일치 후보가 없으면 인용으로 만들지 않습니다. 섹션 순서와 길이, 책·근거 귀속, 목표 분량을 검사한 뒤 두 파일을 저장하며 기존 결과는 덮어쓰지 않습니다.

## Remotion 영상 생성 방향

영상 자동 생성의 최우선 렌더러는 Remotion입니다. 출처 검증이 승인된 실행을 영상 manifest로 변환합니다.

```bash
uv run python scripts/prepare_video.py --run-id "<approved-run-id>"
# 또는
uv run python -m app.cli prepare-video --run-id "<approved-run-id>"
```

명령은 실행 폴더에 `video_manifest.json`을 저장하고 `video/src/data/current-video.json`을 현재 Remotion 입력으로 동기화합니다. 섹션 ID, 시작·종료 시간, 30fps 프레임 범위, 화면 문구, 인용 원문과 출처, 마지막 참고 도서를 보존합니다. 승인되지 않은 대본은 변환을 차단합니다.

```bash
cd video
npm install
npm run dev       # Remotion Studio
npm run lint      # ESLint + TypeScript
npm run build     # Remotion bundle
npm run still     # 대표 프레임
npm run render    # MP4 렌더
```

현재 컴포지션은 1920×1080 편집형 모션 그래픽, 차분한 야간 팔레트, 섹션별 `Sequence`, 최대 2개의 인용 카드와 참고 도서 엔딩 카드를 제공합니다. 음성 합성, 문장 단위 자막 타이밍과 외부 영상 자산은 아직 연결하지 않습니다. 상세 결정은 [Remotion 영상 파이프라인](docs/remotion-video-pipeline.md)에 기록했습니다.

승인 실행의 내레이션 음성은 다음 경로 규칙으로 자동 감지합니다.

```text
video/public/audio/<run-id의 날짜_시간_식별자>/narration.mp3
```

예시:

```text
video/public/audio/20260713_164905_804869/narration.mp3
```

음성이 있으면 Remotion이 Mediabunny로 실제 길이를 측정하고 `calculateMetadata`에서 전체 프레임과 섹션 시간을 비례 조정합니다. 음성 재생 속도는 변경하지 않습니다. 현재는 섹션 단위 근사 싱크이며 정확한 문장 자막은 후속 음성 전사·정렬 단계에서 생성합니다.

## Phase 7 출처 검증

Phase 6 대본의 인용과 책 관련 문단을 원본 Markdown 청크에 대조합니다.

```bash
uv run python scripts/validate_script.py --run-id "<run-id>"
```

CLI에서는 `uv run python -m app.cli validate-script --run-id "<run-id>"`을 사용할 수 있습니다. 파일·행 범위·content hash·책/근거/청크 귀속·직접 인용 일치는 로컬에서 결정적으로 검사합니다. 요약 의미 왜곡, 책 간 혼합, 지원되지 않은 인과관계는 해당 문단에 연결된 제한 청크만 구조화 모델에 전달해 검토합니다.

- `citations.json`: 문단별 출처, 원본 경로와 행 범위, 검증 상태와 문제
- `validation_report.md`: 승인 상태, 고위험 문제와 권장 수정안

고위험 문제가 하나라도 있으면 상태는 `needs_revision`이 되며 최종 승인을 차단합니다. 기존 검증 결과는 덮어쓰지 않습니다.

검증 리포트의 고위험 문단만 권장 수정안으로 교체한 새 불변 리비전을 만들 수 있습니다.

```bash
uv run python scripts/revise_script.py --run-id "<needs_revision-run-id>"
uv run python scripts/validate_script.py --run-id "<new-revision-run-id>"
```

CLI 명령은 `uv run python -m app.cli revise-script --run-id "<run-id>"`입니다. 원본 실행과 이전 리비전은 보존됩니다.

## Editorial Insight 통합

`insights/`에 insight 분석 서비스가 생성한 Markdown 파일을 추가하거나 갱신할 수 있습니다. 파일은 책 근거가 아니라 주제·제목·훅·톤·서사·결말을 정하는 편집 전략으로만 사용합니다. 기본 운영 프로필은 `잠들기전 교양이`입니다.

```bash
uv run python scripts/sync_insights.py
uv run python scripts/suggest_topics.py --count 10
```

동기화 결과는 `data/insights/manifest.json`, 주제 후보는 `data/insights/topic_ideas.json`과 `reports/topic_ideas.md`에 저장됩니다. Phase 4를 실행하면 주제별 `editorial_strategy.json`과 `insight_sources.json`이 실행 폴더에 저장되고 Phase 5·6이 같은 스냅샷을 이어받습니다.

파일명은 한글 조합형 차이를 고려해 정규화하며 content hash로 추가·변경·삭제를 판별합니다. 새로운 insight는 이후 실행부터 적용하고 과거 실행은 바꾸지 않습니다. 우선순위와 상세 운영 규칙은 [Editorial Insight 운영](docs/editorial-insights.md)을 참고하세요.

## FastAPI 로컬 백엔드

Phase 8의 백엔드는 로컬 라이브러리와 생성 결과를 조회하고 Phase 4 연구 및 Phase 5 구성안 작업을 실행하는 FastAPI입니다.

```bash
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

서버 실행 후:

```text
API:      http://127.0.0.1:8000
OpenAPI:  http://127.0.0.1:8000/docs
```

현재 endpoint:

| Method | Path | 용도 |
|---|---|---|
| GET | `/health` | 서버 상태 |
| GET | `/api/library/status` | Markdown·책·청크·임베딩 현황 |
| GET | `/api/runs?limit=50` | 최근 생성 실행과 단계 상태 |
| GET | `/api/runs/{run_id}` | 한 실행의 검증 상태와 산출물 목록 |
| GET | `/api/runs/{run_id}/artifacts/{name}` | 허용된 JSON·Markdown 산출물 조회 |
| POST | `/api/research-jobs` | 주제 옵션으로 Phase 4 연구 작업 생성 |
| POST | `/api/runs/{run_id}/outline-jobs` | 도서 선택 순서를 보존하고 Phase 5 구성안 작업 생성 |
| POST | `/api/runs/{run_id}/script-jobs` | 구성안 편집 리비전을 보존하고 Phase 6 대본 작업 생성 |
| POST | `/api/runs/{run_id}/validation-jobs` | Phase 6 대본의 Phase 7 출처 검증 작업 생성 |
| GET | `/api/jobs?limit=50` | 최근 연구·구성안 작업과 상태 목록 |
| GET | `/api/jobs/{job_id}` | 작업 요청·단계·결과·실패 원인 조회 |
| GET | `/api/jobs/{job_id}/status` | polling용 작업 상태 조회 |

`POST /api/research-jobs`는 `topic`, `duration_minutes`, `target_book_count`, `tone`, `audience`, `desired_lenses`, `desired_emotional_effects`, `excluded_lenses`를 받습니다. 작업은 SQLite에 보존되며 기본적으로 한 번에 하나만 실행합니다. 서버가 재시작되면 실행 중이던 작업은 `interrupted` 실패로 기록됩니다. `insufficient_evidence`는 실행 오류가 아니라 근거 우선 원칙에 따른 정상 파이프라인 결과입니다.

`POST /api/runs/{run_id}/outline-jobs`는 원본 연구 실행 ID와 순서가 있는 `selected_book_ids` 2~4개를 받습니다. 후보 도서 여부와 신뢰도 0.5 이상의 근거를 검사한 뒤 원본 실행을 수정하지 않고 `outputs/<new-run-id>/`에 선택 리비전을 만듭니다. 새 실행에는 `selection_revision.json`으로 원본 실행과 선택 순서를 기록하고, 성공하면 `narrative.json`과 `outline.md`를 추가합니다.

`POST /api/runs/{run_id}/script-jobs`는 확정 제목과 기존 섹션 ID별 수정 제목·목적·순서를 받습니다. 도입과 결론 위치, 섹션 누락·추가 여부를 검사하고 도서·근거 ID와 시간은 원본 구성안에서 그대로 보존합니다. 새 실행의 `narrative_revision.json`이 편집 출처와 섹션 순서를 기록하며, 성공하면 `script_with_sources.md`와 `script.md`를 생성합니다.

`POST /api/runs/{run_id}/validation-jobs`는 완성된 두 대본 산출물을 확인한 뒤 Phase 7 검증을 수행합니다. 결정적 검사로 청크 해시, 원본 파일, 행 범위, 인용 일치, 책·근거·청크 귀속과 도서 제목을 확인하고 제한된 관련 청크만 의미 검토에 사용합니다. 완료 상태는 `approved` 또는 `needs_revision`이며 `citations.json`과 `validation_report.md`를 같은 실행에 추가합니다.

API는 로컬 절대 경로를 응답하지 않고, 정해진 생성 산출물만 조회할 수 있습니다. 원본 Markdown과 임의 로컬 파일은 제공하지 않습니다. CORS는 `ALLOWED_ORIGINS`에 설정한 frontend origin만 허용합니다. 상세 내용은 [로컬 FastAPI](docs/local-api.md)를 참고하세요.

## Next.js 웹 UI

백엔드를 먼저 실행한 뒤 별도 터미널에서 프론트엔드를 시작합니다.

```bash
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`을 엽니다. UI는 라이브러리 상태를 확인하고 주제, 영상 길이, 도서 수, 타겟, 정서적 진입점, 주요 관점, 후반부 확장과 제외 관점을 Phase 4 작업 API로 전달합니다. 작업 상태는 polling하며 완료 후 후보 도서의 검색·주제·편집·정서 점수, 선정 이유와 제안 역할을 표시합니다. 사용자는 2~4권과 내러티브 순서를 확정해 Phase 5 구성안을 생성하고, 제목·중간 섹션 순서·섹션 제목과 목적을 수정한 뒤 Phase 6 대본을 생성할 수 있습니다. 생성된 대본은 내부 출처 표시를 켜고 끌 수 있으며 Phase 7 검증 결과에서 승인 여부, 심각도별 이슈, 문단별 신뢰도와 원본 파일·행 범위를 확인하고 대본·검증 산출물을 내려받을 수 있습니다.

인문 탐구 프리셋은 적용될 값을 먼저 보여주고 명시적으로 적용합니다. 인문학·철학·심리학을 중심으로 자기이해, 관계, 감정, 삶의 의미와 일상 성찰을 연결하며 커리어 계열 기본 제외 관점을 함께 표시합니다.

프론트엔드 검증:

```bash
cd frontend
npm run lint
npm run test
npm run build
npm audit
```

### Vercel 배포와 GitHub 자동 반영

Vercel 프로젝트의 Root Directory는 `frontend`입니다. 프로젝트는 GitHub 저장소의 기본 브랜치와 연결하며, `main`에 푸시된 커밋은 production 배포로 자동 반영합니다. 로컬 개발의 `NEXT_PUBLIC_API_BASE_URL`은 `http://127.0.0.1:8000`, production은 서버 프록시 경로 `/api/local`입니다.

- Vercel project: `voidx-bookscript-agent`
- Production URL: <https://voidx-bookscript-agent.vercel.app>
- Git production branch: `main`
- Root Directory: `frontend`
- Production `NEXT_PUBLIC_API_BASE_URL`: `/api/local`
- Production `LOCAL_BACKEND_URL`: ngrok 개발 도메인
- Production `LOCAL_BACKEND_TOKEN`: Vercel sensitive 환경변수

```bash
cd frontend
vercel link
vercel git connect https://github.com/prodigk/voidx-BookScript-agent.git
vercel --prod
```

Vercel 브라우저는 `/api/local/*`만 호출합니다. Vercel Route Handler가 서버 전용 토큰을 추가해 ngrok HTTPS 터널을 거쳐 로컬 FastAPI로 전달합니다. 토큰이 없는 ngrok의 `/api/*` 요청은 401로 차단되며 Markdown, SQLite와 OpenAI API 키는 계속 로컬에 남습니다.

```dotenv
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://voidx-bookscript-agent.vercel.app
```

현재 Mac에는 다음 로컬 서비스가 등록되어 있습니다.

- `com.voidx.bookscript.tunnel`: ngrok 터널을 로그인 시 자동 시작
- `com.voidx.bookscript.backend-terminal`: Documents 접근 권한이 있는 Terminal에서 FastAPI를 로그인 시 자동 시작
- API 토큰: macOS Keychain과 Vercel sensitive 환경변수에만 저장

## 테스트

```bash
uv run pytest
```

## 현재 아키텍처

- `app/config.py`: YAML 및 환경 변수 설정
- `app/ingestion/`: 파일 탐색, frontmatter, heading, 메타데이터, 진단
- `app/ingestion/chunker.py`: heading·문단 기반 청킹과 행 범위 보존
- `app/retrieval/`: SQLite FTS5 키워드 검색
- `app/retrieval/semantic_search.py`: 로컬 캐시 벡터의 코사인 유사도 검색
- `app/retrieval/hybrid_search.py`: 키워드·의미·메타데이터·다양성 점수 결합
- `app/llm/embeddings.py`: 제한된 청크 배치용 OpenAI 임베딩 클라이언트
- `app/agents/phase4.py`: 주제 분석, 책 랭킹, 근거 큐레이션, 최종 선택
- `app/agents/phase5.py`: 근거 ID 검증, 내러티브 설계, 제목 후보와 영상 구성안 생성
- `app/agents/phase6.py`: 선택 source chunk 기반 대본 생성, 귀속·분량 검증, 내부/최종 대본 분리
- `app/agents/phase7.py`: 원본 행·해시·인용 결정 검사와 제한 청크 기반 의미 검증
- `app/insights/`: insight Markdown 파싱, content-hash manifest, 관련 전략 발췌
- `app/agents/editorial.py`: 주제별 편집 전략과 insight 기반 주제 후보 생성
- `app/video/`: 승인 대본을 검증된 Remotion manifest로 변환
- `app/llm/structured.py`: Responses API Pydantic 구조화 출력과 제한 재시도
- `app/schemas/`: Pydantic 데이터 모델
- `app/storage/`: SQLite 스키마와 전체·증분 인덱싱
- `backend/app/`: FastAPI app factory, CORS, 조회 API와 SQLite 기반 연구·선택·구성안 리비전·대본·검증 작업 실행
- `frontend/`: Next.js 16, TypeScript, Tailwind CSS 기반 주제 입력·후보 선택·구성안 편집·대본·출처 검토 UI
- `scripts/`: 직접 실행 진입점
- `video/`: manifest 기반 Remotion React/TypeScript 컴포지션
- `tests/fixtures/`: 작은 격리 Markdown 테스트 자료

## 알려진 제한 사항

- 저자 본문 추론은 `저자:`, `지은이:`, `글:`, `by` 패턴만 지원합니다.
- 카테고리는 frontmatter가 없으면 `library/` 바로 아래의 첫 디렉터리명으로 추론합니다.
- 동일 문서는 현재 본문 SHA-256이 완전히 같은 경우에만 중복 후보로 봅니다.
- FTS5 `unicode61` 토크나이저와 접두어 검색을 사용하며 한국어 형태소 분석은 아직 지원하지 않습니다.
- 한 줄이 최대 청크 크기보다 길면 같은 원본 행 번호를 공유하는 여러 청크 조각으로 분리됩니다.
- 최소 청크 크기는 heading 경계 및 최대 크기 보존이 우선이므로 모든 경우에 강제되지 않습니다.
- 검색 평가는 아직 fixture 수준이며 실제 주제별 Recall 평가는 Phase 3에서 진행해야 합니다.
- watcher는 실행 중인 로컬 프로세스이므로 터미널을 닫거나 컴퓨터가 잠자기 상태가 되면 변경 감지가 중단됩니다. 재실행 시 누락된 변경을 증분 동기화합니다.
- 벡터 검색은 현재 4천여 청크를 SQLite에서 읽어 Python으로 코사인 유사도를 계산합니다. 데이터가 크게 늘면 sqlite-vec 도입이 필요합니다.
- OpenAI 임베딩 생성에는 API 사용 비용이 발생합니다. watcher는 기본적으로 FTS만 갱신하며 `--embeddings`를 지정한 경우에만 변경 청크의 벡터도 자동 생성합니다.
- 일부 책 제목과 저자가 `unknown`이거나 첫 H1으로 추론되어 Phase 4 랭킹과 표시 품질에 영향을 줍니다.
- 직접 인용의 엄격한 원문 일치 검증은 Phase 7 범위입니다.
- Phase 6은 기본적인 직접 인용 원문 포함 여부만 검사하며 의미 왜곡과 복합 귀속 검토는 Phase 7 범위입니다.
- Phase 4에서 quotation으로 분류됐더라도 원문과 정확히 일치하지 않는 근거는 Phase 6에서 화면 인용으로 사용하지 않고 paraphrase로 강등합니다.
- Remotion은 내레이션 음성과 프레임 기반 장면을 지원하지만 문장 단위 자막 타이밍과 실제 사진·영상 자산은 아직 연결하지 않았습니다.
- Phase 7 의미 검증은 모델 판정도 포함하므로 경계 사례는 사람이 `validation_report.md`와 원문을 함께 검토해야 합니다.
- Insight 기반 주제 후보는 편집 적합성 기준이며 실제 라이브러리 근거 충분성은 Phase 4 검색 전에는 보장하지 않습니다.
- FastAPI 작업 실행은 현재 Phase 4 연구, Phase 5 구성안, Phase 6 대본과 Phase 7 검증까지 지원합니다. 작업 취소·재시도와 부분 수정 작업은 후속 단계입니다.
- 연구 작업은 로컬 단일 프로세스의 FastAPI `BackgroundTasks`로 실행합니다. 서버 종료 후 자동 재개하지 않으며 중단 상태를 명시적으로 기록합니다.
- 구성안 편집은 제목, 섹션 제목·목적, 중간 섹션 순서만 지원합니다. 근거 안전성을 위해 시간·도서·근거 연결과 도입·결론 위치는 잠겨 있습니다.
- 검증 이슈와 원본 위치는 UI에서 확인할 수 있지만 문제가 있는 문단만 안전하게 재작성하고 재검증하는 기능은 아직 연결되지 않았습니다.
- 로컬 Mac이 꺼져 있거나 잠자기·네트워크 단절 상태이면 Vercel 프록시는 503을 반환합니다.

## UI 방향 옵션

Phase 8 주제 입력 UI에는 타겟 시청자, 정서적 진입점, 주요 관점, 확장 주제, 제외 관점을 포함합니다. 인문 탐구 프리셋은 일상의 질문에서 시작해 인문학·철학·심리학으로 해석하고 자기이해·관계·삶의 의미로 확장합니다. 상세 설계 요구사항은 [타겟 시청자 및 영상 방향 UI 요구사항](docs/target-audience-ui-requirements.md)에 기록되어 있습니다.
