# Phase 8 Next.js 프론트엔드

## 현재 흐름

```text
주제와 방향 입력
→ POST /api/research-jobs
→ 작업 상태 polling
→ Phase 4 후보 도서와 선정 근거 조회
→ 브라우저에서 후보 검토
```

프론트엔드는 원본 Markdown과 SQLite를 직접 읽지 않는다. 모든 데이터는 `NEXT_PUBLIC_API_BASE_URL`에 지정한 로컬 FastAPI의 제한된 응답으로만 받는다.

## 디자인 방향

`DESIGN-airbnb.md`의 흰 캔버스, 넓은 여백, 14~20px radius와 `#ff385c` 포인트를 적용했다. 한국어 본문은 시스템에 설치된 Pretendard 또는 Noto Sans KR을 우선하며, 무거운 대시보드 대신 차분한 에디토리얼 작업실로 구성한다.

대표 패턴은 `Research ribbon`이다. 요청 준비, 책과 근거 탐색, 후보 정리의 현재 단계를 색상뿐 아니라 아이콘과 텍스트로 함께 표시한다.

방향 선택은 핵심 옵션을 먼저 보여주고 `더 보기`로 확장한다. 현재 제공 범위는 다음과 같다.

- 정서적 진입점: 위로, 위안, 공감, 안도, 호기심, 용기, 희망, 자기이해, 문제의식, 경각심
- 주요 관점: 철학, 심리학, 사회학, 커리어, 관계, 뇌과학, 문화, 역사, 윤리, 교육, 경제, 조직
- 후반부 확장: 생산성, 동기부여, 실천 방법, 업무 경계, 관계 회복, 자기돌봄, 습관 설계, 감정 조절, 의사결정, 커뮤니케이션, 리더십, 삶의 의미

Phase 4 요청 스키마에 맞춰 정서적 진입점은 최대 8개, 주요 관점과 후반부 확장은 합쳐서 최대 8개까지 선택한다.

## 환경 변수

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

백엔드에는 프론트엔드 origin이 허용되어야 한다.

```dotenv
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## 실행과 검증

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run test
npm run build
npm audit
```

## 현재 경계

- Phase 4 작업만 시작할 수 있다.
- 후보 도서의 선택 변경은 브라우저에서만 유지된다.
- 후보 확정, 순서 저장과 Phase 5 구성안 생성은 다음 API가 필요하다.
- `insufficient_evidence`는 오류가 아니라 별도의 근거 부족 상태로 표시한다.
