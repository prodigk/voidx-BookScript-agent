YouTube Book Script Agent 작업 설계서

1. 프로젝트 개요

1.1 프로젝트명

YouTube Book Script Agent

1.2 프로젝트 목적

로컬에 저장된 약 200개의 도서 관련 Markdown 문서를 분석하고, 사용자가 입력한 주제에 적합한 도서를 검색·선정한 뒤 근거가 되는 내용을 발췌하여 유튜브 영상용 리서치 자료, 구성안, 대본을 생성하는 로컬 기반 에이전트를 구축한다.

이 시스템은 단순한 대본 생성 도구가 아니다.

핵심 목적은 다음과 같다.

1. 사용자의 도서 Markdown 자료를 검색 가능한 지식베이스로 변환한다.
2. 특정 주제와 관련성이 높은 책과 문장을 찾아낸다.
3. 서로 다른 책의 관점을 비교하고 연결한다.
4. 원문 근거에 기반한 영상 스토리라인을 만든다.
5. 검증 가능한 출처와 함께 유튜브 대본을 생성한다.

⸻

2. 핵심 사용자 시나리오

사용자는 다음과 같이 시스템을 사용한다.

주제:
왜 우리는 타인의 평가를 지나치게 의식하는가
영상 길이:
약 12분
사용할 도서 수:
3권
톤:
사색적이고 지적이지만 어렵지 않은 설명
대상:
인문학, 철학, 심리학에 관심 있는 성인 시청자

시스템은 다음 결과물을 생성한다.

1. 주제 분석
2. 검색 키워드와 하위 질문
3. 관련 도서 후보
4. 책별 관련 근거와 발췌
5. 최종 도서 선정
6. 책 사이의 공통점과 차이점
7. 영상 구성안
8. 유튜브 대본
9. 출처 목록
10. 검증 리포트

⸻

3. 프로젝트 범위

3.1 MVP 범위

첫 번째 버전에서는 다음 기능을 구현한다.

문서 처리

* 로컬 디렉터리의 Markdown 파일 자동 탐색
* YAML frontmatter 파싱
* Markdown heading 구조 분석
* 책 제목, 저자, 카테고리 추출
* 문서 본문 청킹
* 원본 파일 경로와 행 번호 보존

검색

* SQLite FTS5 기반 키워드 검색
* 임베딩 기반 의미 검색
* 키워드 검색과 의미 검색을 결합한 하이브리드 검색
* 도서별 관련도 집계
* 같은 책의 청크가 과도하게 노출되지 않도록 제한

리서치

* 주제 분석
* 검색 키워드 확장
* 관련 도서 후보 생성
* 책별 핵심 주장 정리
* 관련 발췌 및 근거 관리
* 최종 도서 2~4권 선정
* 책 사이의 공통점, 차이점, 대립 관점 분석

대본 생성

* 영상 구성안 생성
* 유튜브 내레이션 대본 생성
* 영상 길이에 따른 분량 조정
* 도입부, 본론, 전환부, 결론 구조 지원
* 직접 인용과 요약·해석 구분

검증

* 직접 인용문 원문 일치 여부 확인
* 원문 파일과 행 번호 확인
* 책 제목과 저자 확인
* 근거 없는 주장 탐지
* 대본 문장과 출처 연결

결과 저장

* 리서치 문서
* 도서 선정 결과
* 구성안
* 대본
* 인용 정보
* 검증 리포트

⸻

3.2 MVP 제외 범위

첫 번째 버전에서는 다음 기능을 우선 제외한다.

* 영상 자동 생성
* 이미지 및 영상 소스 자동 수집
* 음성 합성
* YouTube API 업로드
* 썸네일 자동 생성
* 외부 인터넷 검색
* 다중 사용자 기능
* 클라우드 배포
* 복잡한 권한 관리
* 모바일 앱

3.3 후속 영상 생성 방향

자동 영상 생성이 시작되는 후속 단계에서는 Remotion을 최우선 렌더러로 사용한다. Python 파이프라인은 검증된 대본, 안정적인 섹션 ID, 타임코드, 화면 연출 힌트를 제공하고 로컬 React/TypeScript Remotion 프로젝트가 이를 `Sequence` 단위로 렌더링한다. 현재 MVP의 영상 자동 생성 제외 범위는 그대로 유지한다.

⸻

4. 핵심 설계 원칙

4.1 Local-first

모든 Markdown 원본은 로컬에 유지한다.

원본 전체를 매번 LLM API에 전달하지 않는다.

검색을 통해 선별된 청크만 LLM에 전달한다.

⸻

4.2 Evidence-first

대본을 먼저 생성하지 않는다.

다음 순서를 반드시 따른다.

문서 검색
→ 근거 수집
→ 도서 선정
→ 리서치팩 생성
→ 영상 구성
→ 대본 생성
→ 출처 검증

⸻

4.3 원문과 생성문 분리

시스템은 텍스트 유형을 명확하게 구분해야 한다.

quotation      직접 인용
paraphrase     책 내용 요약
interpretation 책 내용에 대한 해석
transition     책과 책 사이의 연결 문장
example        설명을 위한 사례
commentary     영상 제작자의 논평

직접 인용이 아닌 문장을 인용문처럼 표시해서는 안 된다.

⸻

4.4 출처 추적 가능성

모든 청크는 다음 정보를 포함해야 한다.

{
  "chunk_id": "chunk_000123",
  "book_id": "book_001",
  "title": "책 제목",
  "author": "저자",
  "source_file": "library/psychology/book.md",
  "heading_path": [
    "3장",
    "인정 욕구"
  ],
  "start_line": 122,
  "end_line": 146,
  "text": "청크 본문"
}

⸻

4.5 단계별 중간 결과 저장

각 처리 단계의 결과를 저장해야 한다.

이를 통해 전체 파이프라인을 다시 실행하지 않고 특정 단계부터 재실행할 수 있어야 한다.

주제 분석 완료
검색 완료
도서 선정 완료
리서치팩 완료
구성안 완료
대본 완료
검증 완료

⸻

5. 전체 처리 파이프라인

사용자 입력
    ↓
Topic Planner
    ↓
Query Expander
    ↓
Hybrid Retriever
    ↓
Book Ranker
    ↓
Evidence Curator
    ↓
Book Selector
    ↓
Narrative Architect
    ↓
Script Writer
    ↓
Citation Reviewer
    ↓
결과 저장

⸻

6. 에이전트별 역할

6.1 Topic Planner

목적

사용자가 입력한 주제를 검색과 영상 기획이 가능한 형태로 구조화한다.

입력

{
  "topic": "왜 우리는 타인의 평가를 지나치게 의식하는가",
  "duration_minutes": 12,
  "target_book_count": 3,
  "tone": "사색적",
  "audience": "일반 성인"
}

출력

{
  "core_question": "타인의 평가는 어떻게 개인의 정체성과 행동에 영향을 주는가",
  "intent": "인정 욕구와 사회적 비교의 원인을 설명하고 대안을 제시한다",
  "subtopics": [
    "사회적 비교",
    "인정 욕구",
    "자존감",
    "불안",
    "집단과 정체성"
  ],
  "keywords": [
    "타인의 시선",
    "평가",
    "비교",
    "인정",
    "자존감"
  ],
  "search_queries": [
    "타인의 평가와 인정 욕구",
    "사회적 비교가 자존감에 미치는 영향",
    "타인의 시선과 정체성"
  ]
}

⸻

6.2 Query Expander

목적

사용자 주제와 의미적으로 관련된 검색어를 확장한다.

역할

* 유의어 생성
* 반대 개념 생성
* 철학적 표현 생성
* 심리학적 표현 생성
* 실생활 표현 생성
* 책 문장에서 사용될 가능성이 높은 표현 생성

예시

원래 주제:
타인의 평가
확장 검색어:
인정 욕구
사회적 비교
타인의 시선
평판
자존감
소속감
수치심
열등감
타자
사회적 자아

⸻

6.3 Hybrid Retriever

목적

키워드와 의미 기반 검색을 결합하여 관련 청크를 반환한다.

검색 방식

1. SQLite FTS5 키워드 검색
2. Embedding 벡터 검색
3. 검색 결과 정규화
4. 점수 결합
5. 중복 청크 제거
6. 도서별 최대 청크 수 제한

기본 점수 정책

최종 청크 점수 =
키워드 검색 점수 30%
+ 의미 검색 점수 45%
+ 제목·카테고리 일치도 15%
+ 문서 다양성 점수 10%

점수 비율은 설정 파일에서 조정 가능해야 한다.

⸻

6.4 Book Ranker

목적

검색된 청크를 책 단위로 집계하여 관련 도서 후보를 선정한다.

평가 항목

* 주제 관련성
* 관련 청크 수
* 관련 청크의 평균 점수
* 근거의 구체성
* 영상에서 사용할 수 있는 설명 가능성
* 다른 책과 연결할 수 있는 가능성
* 주제에 대한 독자적인 관점

출력 예시

{
  "book_id": "book_014",
  "title": "미움받을 용기",
  "author": "기시미 이치로",
  "score": 0.91,
  "relevance_reason": "인정 욕구와 타인의 기대에서 벗어나는 문제를 직접 다룸",
  "suggested_role": "문제 해결 관점",
  "evidence_chunk_ids": [
    "chunk_0031",
    "chunk_0034"
  ]
}

⸻

6.5 Evidence Curator

목적

도서별로 사용할 수 있는 근거를 정리하고 출처를 구조화한다.

주요 작업

* 직접 인용 후보 추출
* 요약 가능한 주장 추출
* 저자의 핵심 관점 정리
* 유사 근거 통합
* 근거가 약한 주장 제거
* 원문과 해석 분리

출력 예시

{
  "evidence_id": "evidence_001",
  "book_id": "book_014",
  "type": "paraphrase",
  "claim": "타인의 기대에 맞추려는 삶은 자신의 과제를 타인에게 넘기는 결과를 만든다",
  "source_chunk_ids": [
    "chunk_0031",
    "chunk_0034"
  ],
  "confidence": 0.92
}

직접 인용의 경우 다음 구조를 사용한다.

{
  "evidence_id": "evidence_002",
  "book_id": "book_014",
  "type": "quotation",
  "quote": "직접 인용문",
  "source_file": "library/psychology/book.md",
  "start_line": 122,
  "end_line": 126,
  "confidence": 1.0
}

⸻

6.6 Book Selector

목적

영상에 실제로 사용할 도서 2~4권을 최종 선정한다.

선정 기준

주제 관련성
근거 충분성
책별 관점의 차별성
책 사이의 연결 가능성
카테고리 다양성
영상 서사 기여도

선정 방식

예를 들어 3권을 사용할 경우 다음 역할을 배정한다.

책 A: 문제의 원인을 설명
책 B: 다른 관점 또는 반론 제시
책 C: 통합적 해결 방향 제시

제외 사유도 기록

{
  "excluded_books": [
    {
      "book_id": "book_077",
      "reason": "주제와 유사하지만 직접적으로 사용할 근거가 부족함"
    }
  ]
}

⸻

6.7 Narrative Architect

목적

선정된 책들을 하나의 영상 흐름으로 연결한다.

기본 영상 구조

1. 시청자의 일상과 연결되는 질문
2. 문제 상황 또는 사례
3. 첫 번째 책의 설명
4. 두 번째 책의 확장 또는 반론
5. 두 관점 사이의 긴장
6. 세 번째 책을 통한 통합
7. 현실에서 적용할 수 있는 관점
8. 시청자에게 남기는 질문

출력 예시

{
  "title_candidates": [
    "왜 우리는 타인의 시선에서 자유롭지 못할까",
    "타인의 평가가 나를 지배하는 이유",
    "인정받고 싶은 마음은 어디에서 오는가"
  ],
  "core_message": "타인의 평가를 완전히 없앨 수는 없지만, 평가를 삶의 기준으로 삼지 않을 수는 있다",
  "sections": [
    {
      "section_id": "intro",
      "purpose": "문제 제기",
      "estimated_seconds": 60
    },
    {
      "section_id": "book_a",
      "purpose": "사회적 비교의 원인 설명",
      "estimated_seconds": 180
    }
  ]
}

⸻

6.8 Script Writer

목적

영상 구성안과 근거 자료를 바탕으로 자연스러운 한국어 내레이션 대본을 작성한다.

대본 작성 규칙

* 지나치게 문어적이지 않게 작성한다.
* 지적인 내용을 일반 시청자가 이해할 수 있도록 설명한다.
* 한 문장을 지나치게 길게 작성하지 않는다.
* 책 내용을 단순 나열하지 않는다.
* 책과 책 사이에 명확한 전환 문장을 넣는다.
* 영상 전체에 하나의 중심 질문을 유지한다.
* 결론에서 내용을 단정적으로 과도하게 일반화하지 않는다.
* 직접 인용은 필요한 경우에만 제한적으로 사용한다.
* 영상 대본에 출처 ID를 내부 마커로 연결한다.

내부 작성 예시

우리가 타인의 평가를 의식하는 이유는 단순히 자신감이 부족해서가 아닙니다.
인간은 다른 사람과의 관계 속에서 자신의 위치를 확인하도록 진화해 왔기 때문입니다.
[SOURCE:evidence_001]

최종 사용자용 대본에서는 내부 마커를 숨길 수 있어야 한다.

⸻

6.9 Citation Reviewer

목적

대본에 사용된 책 관련 주장을 원문과 비교하여 검증한다.

검증 항목

* 직접 인용이 원문과 정확히 일치하는가
* 인용 범위가 지나치게 길지 않은가
* 요약이 원문의 의미를 왜곡하지 않는가
* 책에 없는 내용을 저자의 주장처럼 표현하지 않았는가
* 서로 다른 책의 주장을 혼합하지 않았는가
* 책 제목과 저자가 정확한가
* 모든 핵심 주장에 근거가 연결되어 있는가

검증 결과

{
  "status": "needs_revision",
  "issues": [
    {
      "severity": "high",
      "script_section": "book_b",
      "issue": "원문에서 확인되지 않는 인과관계가 추가됨",
      "recommended_action": "문장을 완화하거나 근거가 있는 표현으로 수정"
    }
  ]
}

심각한 문제가 있으면 Script Writer 단계로 되돌아가 수정한다.

⸻

7. 입력 데이터 구조

7.1 권장 Markdown 형식

---
title: 미움받을 용기
author: 기시미 이치로
category:
  - 심리
  - 자기계발
tags:
  - 인정 욕구
  - 아들러
  - 인간관계
---
# 책 소개
내용
# 핵심 내용
## 인정 욕구
내용
## 과제의 분리
내용
# 인상적인 문장
내용

YAML frontmatter가 없는 문서도 처리할 수 있어야 한다.

⸻

7.2 메타데이터 추론 우선순위

1. YAML frontmatter
2. Markdown 최상위 제목
3. 파일명
4. 본문 패턴 추론

메타데이터를 확정할 수 없는 경우 unknown으로 저장하고 라이브러리 진단 리포트에 표시한다.

⸻

8. 청킹 전략

8.1 원칙

고정 글자 수로만 자르지 않는다.

Markdown heading 구조를 우선 사용한다.

문서
→ H1
→ H2
→ H3
→ 문단

8.2 기본 청크 크기

목표 크기: 500~1,000자
최대 크기: 1,500자
최소 크기: 200자
중첩 범위: 100~200자

설정값으로 변경 가능해야 한다.

8.3 청크 보존 정보

원본 파일
책 ID
제목
저자
카테고리
heading 경로
시작 행
종료 행
청크 텍스트
청크 해시

⸻

9. 데이터베이스 설계

SQLite를 기본 저장소로 사용한다.

9.1 books 테이블

CREATE TABLE books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    category TEXT,
    tags TEXT,
    source_file TEXT NOT NULL,
    content_hash TEXT,
    created_at TEXT,
    updated_at TEXT
);

9.2 chunks 테이블

CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL,
    heading_path TEXT,
    start_line INTEGER,
    end_line INTEGER,
    content TEXT NOT NULL,
    content_hash TEXT,
    embedding_id TEXT,
    FOREIGN KEY(book_id) REFERENCES books(id)
);

9.3 FTS 테이블

CREATE VIRTUAL TABLE chunks_fts USING fts5(
    chunk_id,
    title,
    author,
    heading_path,
    content
);

9.4 pipeline_runs 테이블

CREATE TABLE pipeline_runs (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    status TEXT NOT NULL,
    config_json TEXT,
    current_stage TEXT,
    created_at TEXT,
    updated_at TEXT
);

9.5 artifacts 테이블

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT,
    FOREIGN KEY(run_id) REFERENCES pipeline_runs(id)
);

⸻

10. 프로젝트 폴더 구조

youtube-book-agent/
├── AGENTS.md
├── PROJECT_SPEC.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── library/
│   ├── philosophy/
│   ├── psychology/
│   ├── culture/
│   ├── technology/
│   ├── career/
│   └── self-development/
│
├── metadata/
│   ├── books.yaml
│   └── categories.yaml
│
├── config/
│   ├── default.yaml
│   ├── retrieval.yaml
│   └── script_style.yaml
│
├── prompts/
│   ├── system_prompt.md
│   ├── topic_planner.md
│   ├── query_expander.md
│   ├── book_ranker.md
│   ├── evidence_curator.md
│   ├── book_selector.md
│   ├── narrative_architect.md
│   ├── script_writer.md
│   └── citation_reviewer.md
│
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── pipeline.py
│   │
│   ├── ingestion/
│   │   ├── markdown_loader.py
│   │   ├── frontmatter_parser.py
│   │   ├── metadata_parser.py
│   │   ├── chunker.py
│   │   └── indexer.py
│   │
│   ├── retrieval/
│   │   ├── keyword_search.py
│   │   ├── vector_search.py
│   │   ├── hybrid_search.py
│   │   ├── reranker.py
│   │   └── book_ranker.py
│   │
│   ├── agents/
│   │   ├── topic_planner.py
│   │   ├── query_expander.py
│   │   ├── evidence_curator.py
│   │   ├── book_selector.py
│   │   ├── narrative_architect.py
│   │   ├── script_writer.py
│   │   └── citation_reviewer.py
│   │
│   ├── schemas/
│   │   ├── book.py
│   │   ├── chunk.py
│   │   ├── topic.py
│   │   ├── evidence.py
│   │   ├── narrative.py
│   │   ├── script.py
│   │   └── validation.py
│   │
│   ├── storage/
│   │   ├── database.py
│   │   ├── book_repository.py
│   │   ├── chunk_repository.py
│   │   └── run_repository.py
│   │
│   ├── llm/
│   │   ├── client.py
│   │   ├── structured_output.py
│   │   └── prompt_loader.py
│   │
│   └── utils/
│       ├── hashing.py
│       ├── logging.py
│       ├── text.py
│       └── file_paths.py
│
├── scripts/
│   ├── audit_library.py
│   ├── build_index.py
│   ├── rebuild_index.py
│   ├── inspect_search.py
│   └── evaluate_retrieval.py
│
├── ui/
│   └── streamlit_app.py
│
├── data/
│   ├── database.sqlite
│   ├── vector_index/
│   ├── cache/
│   └── evaluations/
│
├── outputs/
│
└── tests/
    ├── fixtures/
    ├── test_markdown_loader.py
    ├── test_metadata_parser.py
    ├── test_chunker.py
    ├── test_keyword_search.py
    ├── test_hybrid_search.py
    ├── test_book_ranker.py
    └── test_citation_reviewer.py

⸻

11. 기술 스택

필수

Python              3.12 이상
패키지 관리          uv
LLM API             OpenAI Responses API
구조 검증            Pydantic
CLI                 Typer
데이터베이스          SQLite
키워드 검색          SQLite FTS5
테스트               pytest
설정                 YAML
환경변수             python-dotenv

선택

벡터 검색            sqlite-vec 또는 Chroma
UI                  Streamlit
상태 그래프           LangGraph
Markdown 파싱        markdown-it-py
YAML frontmatter     python-frontmatter

초기 버전은 일반 Python 함수 기반 파이프라인으로 구현한다.

LangGraph는 다음 조건이 발생할 때 도입한다.

* 검증 실패 시 자동 재작성
* 사용자 승인 단계
* 복잡한 분기
* 단계별 재실행
* 장기 실행 상태 저장

⸻

12. CLI 요구사항

라이브러리 진단

uv run python scripts/audit_library.py

출력:

reports/library_audit.md
metadata/books.yaml

인덱스 생성

uv run python scripts/build_index.py

검색 테스트

uv run python scripts/inspect_search.py \
  --query "타인의 평가와 인정 욕구" \
  --limit 20

전체 파이프라인 실행

uv run python -m app.cli generate \
  --topic "왜 우리는 타인의 평가를 지나치게 의식하는가" \
  --duration 12 \
  --books 3 \
  --tone reflective

특정 단계부터 재실행

uv run python -m app.cli resume \
  --run-id run_20260713_001 \
  --from-stage narrative

⸻

13. 결과물 구조

outputs/
└── 2026-07-13_타인의-평가/
    ├── input.json
    ├── topic_analysis.json
    ├── search_results.json
    ├── candidate_books.json
    ├── selected_books.json
    ├── evidence.json
    ├── research.md
    ├── narrative.json
    ├── outline.md
    ├── script_with_sources.md
    ├── script.md
    ├── citations.json
    └── validation_report.md

⸻

14. 리서치 문서 형식

# 영상 리서치
## 입력 주제
## 핵심 질문
## 영상에서 전달할 중심 메시지
## 하위 주제
## 선정 도서
### 도서 1
- 제목:
- 저자:
- 영상에서의 역할:
- 핵심 주장:
- 관련 근거:
- 사용할 수 있는 발췌:
- 다른 책과의 연결점:
### 도서 2
## 도서 간 공통점
## 도서 간 차이점
## 대립하는 관점
## 영상 스토리라인 제안
## 사용 시 주의할 주장
## 출처 목록

⸻

15. 유튜브 대본 형식

# 제목
## 영상 기본 정보
- 예상 길이:
- 대상 시청자:
- 핵심 메시지:
- 사용 도서:
## Hook
대본
## 문제 제기
대본
## Chapter 1
대본
## Chapter 2
대본
## Chapter 3
대본
## 결론
대본
## 엔딩 질문
대본
## 참고 도서
- 도서명 / 저자

⸻

16. 설정 파일 예시

config/default.yaml

project:
  language: ko
  library_path: library
  output_path: outputs
  database_path: data/database.sqlite
chunking:
  min_chars: 200
  target_chars: 800
  max_chars: 1500
  overlap_chars: 150
retrieval:
  keyword_limit: 50
  vector_limit: 50
  final_chunk_limit: 30
  max_chunks_per_book: 5
book_selection:
  candidate_count: 10
  default_selected_count: 3
  min_selected_count: 2
  max_selected_count: 4
script:
  default_duration_minutes: 12
  korean_chars_per_minute: 320
  quotation_ratio_max: 0.1
validation:
  require_source_for_book_claims: true
  fail_on_invalid_quote: true
  fail_on_missing_book_metadata: false

config/retrieval.yaml

weights:
  keyword: 0.30
  semantic: 0.45
  metadata: 0.15
  diversity: 0.10
diversity:
  enabled: true
  same_book_penalty: 0.15
  category_bonus: 0.05

⸻

17. Pydantic 스키마 원칙

모든 LLM 출력은 자유 텍스트가 아니라 Pydantic 모델로 검증한다.

예시:

from pydantic import BaseModel, Field
class TopicAnalysis(BaseModel):
    core_question: str
    intent: str
    subtopics: list[str] = Field(min_length=2)
    keywords: list[str] = Field(min_length=3)
    search_queries: list[str] = Field(min_length=2)

LLM 출력 검증에 실패하면 다음 순서로 처리한다.

1. JSON 복구
2. 동일 프롬프트 재시도
3. 더 엄격한 출력 지시로 재시도
4. 실패 기록 후 파이프라인 중단

⸻

18. 라이브러리 진단 요구사항

최초 구현 단계에서 전체 Markdown 파일을 분석하여 다음 리포트를 생성한다.

전체 파일 수
정상 파싱 파일 수
YAML frontmatter 포함 비율
제목 추출 성공률
저자 추출 성공률
카테고리 분포
평균 문서 길이
가장 긴 문서
가장 짧은 문서
heading 사용 비율
중복 가능성이 있는 문서
파일명 규칙
인용문 표기 패턴
개인 메모 표기 패턴
파싱 오류 목록

리포트 파일:

reports/library_audit.md

⸻

19. 테스트 전략

19.1 단위 테스트

Markdown Loader

* 재귀적으로 .md 파일을 찾는가
* 숨김 파일을 제외하는가
* UTF-8 문서를 읽는가
* 잘못된 인코딩을 기록하는가

Metadata Parser

* frontmatter를 읽는가
* 제목과 저자를 추론하는가
* 파일명을 fallback으로 사용하는가

Chunker

* heading 구조를 유지하는가
* 행 번호가 정확한가
* 최대 크기를 넘지 않는가
* 너무 짧은 청크를 병합하는가

Search

* 키워드 검색이 정상 동작하는가
* 검색 결과에 원본 경로가 포함되는가
* 동일한 책의 결과 수가 제한되는가

Citation Reviewer

* 존재하지 않는 인용을 탐지하는가
* 행 번호가 잘못된 출처를 탐지하는가
* 인용문 변경을 탐지하는가

⸻

19.2 검색 평가

대표 주제 10~20개를 평가 데이터로 관리한다.

- topic: 타인의 평가와 인정 욕구
  expected_books:
    - 미움받을 용기
  expected_keywords:
    - 인정 욕구
    - 타인의 시선
- topic: 기술은 인간의 사고방식을 어떻게 바꾸는가
  expected_categories:
    - technology
    - philosophy

평가 지표:

Recall@5
Recall@10
관련 도서 상위 노출률
관련 청크 정확도
도서 다양성
동일 도서 과다 노출률

⸻

20. 오류 처리

문서 파싱 실패

* 전체 실행을 중단하지 않는다.
* 오류 파일을 기록한다.
* 진단 리포트에 포함한다.

검색 결과 부족

* 검색어를 자동 확장한다.
* 키워드 비중을 높여 재검색한다.
* 관련 도서 수를 줄인다.
* 근거 부족 상태를 결과에 표시한다.

근거 부족

대본을 억지로 생성하지 않는다.

{
  "status": "insufficient_evidence",
  "message": "선택한 주제를 충분히 뒷받침할 근거가 부족합니다."
}

검증 실패

* 문제가 있는 문장을 표시한다.
* 해당 문장만 재작성한다.
* 최대 재시도 횟수를 제한한다.
* 반복 실패 시 사용자 검토 대상으로 남긴다.

⸻

21. 로깅 요구사항

다음 정보를 로그로 남긴다.

실행 ID
현재 처리 단계
처리한 문서 수
생성한 청크 수
검색어
검색 결과 수
선정 도서
LLM 호출 횟수
토큰 사용량
재시도 횟수
오류 메시지
전체 실행 시간

민감한 API 키나 전체 원문은 로그에 남기지 않는다.

⸻

22. 개발 단계

Phase 0. 프로젝트 초기화

목표

기본 프로젝트 구조와 개발 환경을 만든다.

작업

* uv 프로젝트 생성
* 기본 디렉터리 생성
* 환경 변수 설정
* 로깅 설정
* SQLite 초기화
* 테스트 환경 구성

완료 조건

uv sync 성공
pytest 실행 성공
CLI help 실행 성공

⸻

Phase 1. 라이브러리 진단

목표

현재 Markdown 문서 구조를 파악한다.

작업

* Markdown 파일 탐색
* frontmatter 분석
* heading 구조 분석
* 제목과 저자 추출
* 통계 리포트 생성

산출물

reports/library_audit.md
metadata/books.yaml

⸻

Phase 2. 문서 인덱싱

목표

Markdown 문서를 검색 가능한 형태로 변환한다.

작업

* 구조 기반 청킹
* 행 번호 보존
* 책 및 청크 테이블 저장
* FTS5 인덱스 생성
* 변경 파일만 재인덱싱

완료 조건

모든 정상 문서가 DB에 저장됨
각 청크에 원본 경로와 행 번호가 있음
키워드 검색 가능

⸻

Phase 3. 하이브리드 검색

목표

키워드와 의미 검색을 결합한다.

작업

* 임베딩 생성
* 벡터 인덱스 저장
* 점수 정규화
* 하이브리드 점수 계산
* 도서 다양성 로직 구현
* 검색 결과 검사 CLI 제작

⸻

Phase 4. 주제 분석과 도서 선정

목표

사용자 주제를 분석하고 최종 도서를 선정한다.

작업

* Topic Planner
* Query Expander
* Book Ranker
* Evidence Curator
* Book Selector
* 모든 새 실행에서 인문학·철학·심리학을 핵심 편집 범위로 적용
* 커리어·생산성·조직관리·성과 중심 관점은 기본 제외

산출물

topic_analysis.json
candidate_books.json
selected_books.json
evidence.json
research.md

⸻

Phase 5. 영상 구성안 생성

목표

여러 책을 하나의 스토리라인으로 연결한다.

작업

* 중심 메시지 생성
* 책별 역할 지정
* 영상 섹션 생성
* 섹션별 예상 시간 계산
* 제목 후보 생성

산출물

narrative.json
outline.md

⸻

Phase 6. 대본 생성

목표

내레이션 가능한 한국어 유튜브 대본을 작성한다.

작업

* 영상 길이 기준 분량 산정
* 섹션별 대본 생성
* 문체 통일
* 출처 ID 연결
* 최종 대본 합성
* 본문에서는 책 제목과 저자를 반복 노출하지 않고 결말에서 참고 도서를 일괄 안내
* 원문과 일치하는 짧은 책 구절을 화면 인용 장면으로 최대 2개 사용

산출물

script_with_sources.md
script.md

⸻

Phase 7. 검증

목표

대본과 원문 근거를 비교한다.

작업

* 직접 인용 확인
* 요약 의미 확인
* 출처 누락 확인
* 책 정보 확인
* 오류 문장 재작성

산출물

citations.json
validation_report.md

⸻

Phase 7.5. Editorial Insight 통합

목표

외부 insight 분석 서비스가 생성한 Markdown을 주제 선정과 영상 편집 전략에 지속 반영한다.

원칙

* insight는 편집 전략이며 책의 사실 근거가 아니다.
* 사용자 직접 설정을 insight보다 우선한다.
* 운영 채널, 카테고리, 레퍼런스 채널의 우선순위를 구분한다.
* 파일 content hash로 추가, 수정, 삭제를 감지한다.
* 실행별 사용 insight ID와 hash를 저장해 과거 결과를 재현한다.
* 기존 실행 결과는 새로운 insight로 자동 변경하지 않는다.

산출물

data/insights/manifest.json
data/insights/topic_ideas.json
reports/topic_ideas.md
outputs/<run-id>/editorial_strategy.json
outputs/<run-id>/insight_sources.json

⸻

Phase 7.6. Remotion 영상 준비

목표

출처 검증이 승인된 대본만 로컬 Remotion 프로젝트의 영상 입력으로 변환한다.

원칙

* `citations.json`이 approved이고 invalid 항목이 없을 때만 변환한다.
* 섹션 ID, 초 단위 시간, FPS, 프레임 범위, 내레이션과 인용 출처를 보존한다.
* 한 섹션은 하나의 Remotion `Sequence`로 매핑한다.
* 원문 인용 카드는 최대 2개이며 책 제목과 원본 행 위치를 표시한다.
* 마지막 장면에서 참고 도서를 일괄 표시한다.
* 영상 프로젝트는 로컬에서 실행하며 Markdown 원본이나 API 키를 포함하지 않는다.

산출물

outputs/<run-id>/video_manifest.json
video/src/data/current-video.json
video/ Remotion React/TypeScript 프로젝트

현재 범위는 데이터 기반 모션 그래픽과 로컬 미리보기까지다. 음성 합성, 자막 타이밍, 외부 영상 자산 수집과 YouTube 업로드는 별도 후속 단계로 둔다.

⸻

Phase 8. FastAPI + Next.js Web UI

목표

CLI 없이도 파이프라인을 사용할 수 있게 한다.

아키텍처 결정

이 문서의 초기 초안은 Streamlit UI를 제안했지만 현재 AGENTS.md의 웹 아키텍처는 FastAPI 로컬 백엔드와 Next.js TypeScript 프론트엔드를 요구한다. Streamlit 표기는 레거시 초안으로 간주하고 현행 구현은 FastAPI + Next.js를 사용한다. 로컬 Markdown과 SQLite는 FastAPI가 접근하며 프론트엔드는 파일 경로가 아닌 제한된 API 응답만 사용한다.

1차 백엔드 범위

* health check
* 라이브러리, 책, 청크, 임베딩 상태
* 생성 실행 목록과 단계 상태
* allowlist 기반 생성 산출물 조회
* 승인된 frontend origin만 허용하는 CORS
* 원본 Markdown 및 임의 로컬 파일 접근 차단
* Phase 4 연구 요청과 SQLite 기반 작업 상태 보존
* 동시 실행 제한 및 서버 재시작 시 중단 작업 기록

후속 범위

* 검색 및 후보 도서 검토 API
* Phase 5~7 단계별 생성 작업과 진행 상태 API

1차 프론트엔드 범위

* Next.js 16 App Router와 TypeScript
* DESIGN-airbnb.md 토큰 기반 반응형 주제 입력
* 타겟·정서·주요 관점·확장·제외 옵션
* Phase 4 작업 생성과 상태 polling
* 후보 도서의 점수·선정 이유·역할 검토
* 로딩·근거 부족·실패 상태

후속 프론트엔드 범위

* 후보 선택·순서 저장
* Phase 5~7 단계별 검토와 재생성
* 산출물 다운로드

주요 화면

주제 입력
영상 길이 선택
도서 수 선택
톤 선택
카테고리 선택
검색 결과 확인
도서 후보 선택
구성안 확인
대본 생성
대본 다운로드

⸻

23. UI 초안

화면 1. 주제 입력

주제
[                                          ]
영상 길이
[8분] [12분] [20분]
도서 수
[2권] [3권] [4권]
톤
[사색적] [지적] [실용적] [스토리텔링]
카테고리
[인문학] [철학] [심리학]
[자료 검색]

23.1 타겟 시청자와 영상 방향 옵션

주제 입력 화면은 대상 시청자, 정서적 진입점, 주요 관점, 확장 주제, 제외 관점을 개별적으로 설정할 수 있어야 한다.

현재 채널 방향은 인문학·철학·심리학에 집중한다. 주제는 일상의 감정과 질문에서 시작해 자기이해, 관계, 감정 조절, 삶의 의미와 일상 성찰로 확장한다. 커리어·생산성·조직관리·성과 중심 문맥은 모든 새 실행에서 기본 제외한다.

프리셋은 편집 가능한 초기값이며 사용자의 직접 선택을 숨기거나 덮어쓰지 않는다. 상세 요구사항은 `docs/target-audience-ui-requirements.md`를 따른다.

화면 2. 도서 후보

후보 도서 10권
체크박스
도서명
저자
관련도
선정 이유
관련 근거 수
주요 관점
[최종 도서 선택]

화면 3. 구성안

제목 후보
핵심 메시지
영상 섹션
책별 역할
예상 길이
[대본 생성]

화면 4. 대본

대본
출처 표시 ON/OFF
검증 문제
수정 제안
[Markdown 다운로드]
[JSON 다운로드]

⸻

24. 보안 및 저작권 관련 내부 원칙

* 원본 Markdown은 로컬에 유지한다.
* API에는 필요한 청크만 전달한다.
* 직접 인용은 최소화한다.
* 긴 원문을 연속해서 대본에 사용하지 않는다.
* 요약과 해석 중심으로 대본을 구성한다.
* 원문이 불완전하거나 출처가 불명확한 경우 이를 명시한다.
* 생성된 문장을 저자의 직접 발언처럼 표현하지 않는다.

⸻

25. 완료 기준

MVP는 다음 조건을 만족하면 완료로 판단한다.

1. 200개 내외 Markdown 파일을 자동 탐색할 수 있다.
2. 각 문서를 구조 기반으로 청킹할 수 있다.
3. 모든 청크에 원본 경로와 행 번호가 보존된다.
4. 특정 주제로 관련 도서 10권을 검색할 수 있다.
5. 최종 도서 2~4권을 선정할 수 있다.
6. 도서별 근거와 핵심 주장을 정리할 수 있다.
7. 여러 책을 하나의 영상 구조로 연결할 수 있다.
8. 8~20분 분량의 한국어 대본을 생성할 수 있다.
9. 직접 인용과 생성 문장을 구분할 수 있다.
10. 대본의 주요 책 관련 주장에 출처가 연결된다.
11. 검증 결과를 별도 리포트로 저장할 수 있다.
12. 전체 결과를 Markdown과 JSON으로 저장할 수 있다.
13. 주요 모듈에 자동 테스트가 존재한다.

⸻

26. Codex 개발 원칙

Codex는 작업 전에 다음 파일을 반드시 읽는다.

AGENTS.md
PROJECT_SPEC.md
README.md

한 번에 전체 시스템을 구현하지 않는다.

각 Phase별로 다음 절차를 따른다.

1. 현재 코드와 문서 확인
2. 작업 범위 정리
3. 필요한 파일 구현
4. 테스트 작성
5. 테스트 실행
6. 오류 수정
7. README 업데이트
8. 변경 사항 요약

기능 구현 시 다음 사항을 지킨다.

* 타입 힌트를 사용한다.
* Pydantic 스키마를 사용한다.
* 함수와 클래스의 책임을 작게 유지한다.
* 하드코딩된 경로를 사용하지 않는다.
* 설정값은 YAML 또는 환경 변수로 분리한다.
* 원본 Markdown 파일을 수정하지 않는다.
* 테스트 없이 핵심 기능을 완료 처리하지 않는다.
* 기존 테스트를 삭제해 통과시키지 않는다.
* 실패한 문서는 조용히 무시하지 않고 기록한다.

⸻

27. Codex 최초 실행 프롬프트

Read AGENTS.md and PROJECT_SPEC.md before making any changes.
Initialize the YouTube Book Script Agent project.
For this iteration, implement only Phase 0 and Phase 1.
Scope:
1. Create the Python 3.12 project using uv.
2. Create the project directory structure described in PROJECT_SPEC.md.
3. Add configuration loading from YAML and environment variables.
4. Implement recursive Markdown file discovery.
5. Implement YAML frontmatter parsing.
6. Analyze Markdown heading structures.
7. Extract or infer title, author, category, and tags.
8. Generate a library audit report.
9. Generate metadata/books.yaml.
10. Add unit tests for file discovery, frontmatter parsing, and metadata inference.
11. Add a CLI command to run the library audit.
12. Update README.md with installation and usage instructions.
Constraints:
- Do not implement embeddings, retrieval, agents, or script generation yet.
- Do not modify source Markdown files.
- Preserve compatibility with Korean file names and Korean text.
- Use pathlib, Pydantic, Typer, pytest, and python-frontmatter.
- Use type hints.
- Record parsing failures instead of stopping the full process.
- Create small fixture Markdown files for tests.
- Run all tests before finishing.
Expected command:
uv run python scripts/audit_library.py
Expected outputs:
reports/library_audit.md
metadata/books.yaml
At the end:
1. Run pytest.
2. Show the final directory tree.
3. Summarize implemented features.
4. List known limitations.
5. Recommend the next development step.

⸻

28. Phase 2 Codex 프롬프트

Read AGENTS.md, PROJECT_SPEC.md, README.md, and the existing code first.
Implement Phase 2: Markdown chunking and SQLite indexing.
Scope:
1. Create Pydantic models for Book and Chunk.
2. Implement heading-aware Markdown chunking.
3. Preserve source file paths, heading paths, and exact line ranges.
4. Add configurable minimum, target, maximum, and overlap sizes.
5. Create SQLite tables for books and chunks.
6. Create an SQLite FTS5 index.
7. Implement full indexing and incremental re-indexing using content hashes.
8. Add a build-index script.
9. Add a CLI command for keyword search.
10. Add unit tests for line ranges, chunk sizes, heading preservation, indexing, and search.
Do not implement embeddings or LLM agents yet.
Expected commands:
uv run python scripts/build_index.py
uv run python scripts/inspect_search.py --query "인정 욕구" --limit 10
At the end, run all tests and update README.md.

⸻

29. Phase 3 이후 구현 우선순위

1순위: 인덱싱 정확도
2순위: 출처 추적
3순위: 검색 품질
4순위: 도서 선정 품질
5순위: 리서치 문서 품질
6순위: 영상 구성 품질
7순위: 대본 문체
8순위: UI

대본 생성 기능을 서두르지 않는다.

검색과 근거 관리가 안정화된 이후 대본 생성을 구현한다.
