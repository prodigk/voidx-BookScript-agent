# 로컬 FastAPI 백엔드

## 목적

Next.js UI가 로컬 Markdown 또는 SQLite에 직접 접근하지 않고 필요한 상태와 생성 산출물만 조회하도록 제한된 HTTP 경계를 제공한다.

```text
Next.js UI
→ http://127.0.0.1:8000
→ FastAPI
→ local SQLite / outputs
```

Vercel에 배포된 프론트엔드는 사용자의 로컬 파일을 직접 읽을 수 없다. 로컬 백엔드가 실행 중이고 브라우저에서 접근 가능한 경우에만 `NEXT_PUBLIC_API_BASE_URL`을 통해 연결한다. 외부 인터넷에 백엔드 포트를 공개하는 구성은 현재 지원하지 않는다.

## 실행

```bash
uv sync
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

환경 변수:

```dotenv
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
BACKEND_MAX_CONCURRENT_JOBS=1
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`ALLOWED_ORIGINS=*`는 사용하지 않는다. 필요한 frontend origin만 쉼표로 지정한다.

## Endpoint

### `GET /health`

프로세스가 요청을 처리할 수 있는지 확인한다.

### `GET /api/library/status`

원본 경로를 노출하지 않고 다음 수치를 반환한다.

- 발견한 Markdown 수
- SQLite 책과 청크 수
- 전체 임베딩 수
- 현재 모델·차원의 임베딩 수
- 마지막 인덱싱 시각

### `GET /api/runs`

최근 불변 실행을 반환한다. 상태는 다음 중 하나다.

```text
started
research_complete
outline_ready
script_ready
needs_revision
approved
```

### `GET /api/runs/{run_id}`

한 실행의 주제, 상태, 검증 건수와 이용 가능한 산출물을 반환한다.

### `GET /api/runs/{run_id}/artifacts/{artifact_name}`

서버 allowlist에 등록된 생성 JSON과 Markdown만 반환한다. `?download=true`이면 attachment header를 추가한다.

### `POST /api/research-jobs`

Phase 4의 `주제 분석 → 검색어 확장 → 책 랭킹 → 근거 큐레이션 → 최종 도서 선택`을 실행한다. HTTP 응답은 `202 Accepted`와 영속 작업 ID를 즉시 반환한다.

```json
{
  "topic": "일이 나를 삼키지 않게 하는 커리어의 태도",
  "duration_minutes": 12,
  "target_book_count": 3,
  "tone": "사색적",
  "audience": "직장인",
  "desired_lenses": ["심리적 위안", "생산성"],
  "desired_emotional_effects": ["공감", "안도"],
  "excluded_lenses": []
}
```

기본 동시 실행 수는 1이다. 이미 `queued` 또는 `running` 작업이 있으면 `409 Conflict`를 반환한다. 설정 한도는 `BACKEND_MAX_CONCURRENT_JOBS`로 조정할 수 있지만 로컬 SQLite와 API 비용 보호를 위해 1을 권장한다.

### `POST /api/runs/{run_id}/outline-jobs`

검토한 후보 가운데 2~4권을 영상에 등장할 순서대로 확정하고 Phase 5 내러티브를 생성한다.

```json
{
  "source_run_id": "20260713_164802_...",
  "selected_book_ids": ["book_a", "book_c", "book_b"]
}
```

서버는 ID 중복, 후보 포함 여부, 책마다 신뢰도 0.5 이상의 근거가 있는지 검사한다. 통과하면 원본 실행은 그대로 두고 새 `selection-revision` 실행 폴더를 만든다. `selection_revision.json`은 원본 실행과 선택 순서를 기록하며, 작업이 성공하면 같은 새 실행에 `narrative.json`과 `outline.md`가 생성된다. 선택 리비전까지 성공하고 모델 호출이 실패한 경우에도 새 실행 ID는 작업 기록에 남아 실패 지점을 확인할 수 있다.

### `POST /api/runs/{run_id}/script-jobs`

사용자가 확정한 제목과 구성안 편집을 새 리비전으로 저장한 뒤 Phase 6 대본을 생성한다.

구조 예시이며 실제 요청의 `sections`에는 기존 섹션 전체를 포함해야 한다.

```json
{
  "source_run_id": "20260714_...-selection-revision",
  "selected_title": "일에서 나를 되찾는 법",
  "sections": [
    {
      "section_id": "hook",
      "title": "퇴근해도 끝나지 않는 일",
      "purpose": "시청자의 감정에서 질문을 시작한다"
    }
  ]
}
```

요청은 기존 섹션 전체를 정확히 한 번씩 포함해야 한다. 제목과 목적, 중간 섹션 순서만 수정할 수 있고 도입은 첫 번째, 결론은 마지막으로 고정된다. 서버는 원본의 시간·책·근거 ID·핵심 포인트를 복사해 변경 요청이 출처 연결을 훼손하지 못하게 한다. 새 실행에는 `narrative_revision.json`, 갱신된 `narrative.json`·`outline.md`, 생성 후 `script_with_sources.md`·`script.md`가 저장된다.

### `POST /api/runs/{run_id}/validation-jobs`

Phase 6 대본을 원본 Markdown과 인덱스 청크에 대조하는 Phase 7 작업을 생성한다.

```json
{
  "source_run_id": "20260714_...-script-revision"
}
```

`script.md`와 `script_with_sources.md`가 모두 있어야 하며 이미 `citations.json` 또는 `validation_report.md`가 존재하면 중복 검증을 차단한다. 검증은 원본 파일 경계, 행 범위, content hash, 직접 인용, 책·근거·청크 귀속과 최종 참고 도서 표기를 결정적으로 검사한다. 의미 기반 요약·해석 검토에는 대본에 연결된 제한 청크만 전달한다. 작업 결과의 `pipeline_status`는 `approved` 또는 `needs_revision`이고 생성된 두 검증 산출물은 allowlist API로 조회·다운로드할 수 있다.

### `GET /api/jobs`

최근 연구와 구성안 작업을 반환한다. 작업 상태는 `queued`, `running`, `succeeded`, `failed`이며 세부 단계와 파이프라인 결과를 함께 제공한다.

### `GET /api/jobs/{job_id}` 및 `/api/jobs/{job_id}/status`

한 작업의 입력 옵션, 현재 상태, 단계, 생성 `run_id`, 완료 시각 또는 제한된 실패 원인을 반환한다. UI polling에는 `/status`를 사용할 수 있다. 근거가 부족한 실행은 `status=succeeded`, `stage=insufficient_evidence`, `pipeline_status=insufficient_evidence`로 표현한다.

## 보안 경계

- run ID는 `outputs/` 바로 아래 디렉터리만 허용한다.
- path traversal과 symlink 기반 외부 접근을 차단한다.
- artifact 이름은 서버 allowlist로 제한한다.
- 원본 Markdown 파일은 제공하지 않는다.
- 로컬 절대 경로는 상태 및 실행 목록 응답에 포함하지 않는다.
- API 키는 응답하거나 브라우저에 전달하지 않는다.
- 현재 CORS method는 `GET`, `POST`, `OPTIONS`만 허용한다.
- 작업 요청은 Pydantic으로 길이, 도서 수, 영상 길이와 옵션 개수를 검증한다.
- 서버 시작 시 이전 프로세스에서 남은 `queued`, `running` 작업은 `interrupted` 실패로 확정한다.

## 다음 백엔드 슬라이스

Phase 4 후보 선택, Phase 5 구성안 편집, Phase 6 대본과 Phase 7 검증 결과 검토까지 연결되었다. 다음 슬라이스는 검증 문제가 있는 부분만 안전하게 수정하는 작업이다.

1. 문제가 있는 문단만 근거 범위 안에서 재작성하는 리비전
2. 수정 리비전의 Phase 7 재검증
3. 승인 대본과 Remotion manifest 연결
4. 작업 취소와 명시적 재시도
5. 새로고침 후 작업 상태 복원
