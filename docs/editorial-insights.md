# Editorial Insight 운영

## 역할

`insights/`의 Markdown은 주제 선정, 제목 문법, 시청자 상태, 훅, 영상 길이, 서사와 결말을 위한 편집 전략이다. 책의 사실 주장이나 인용 근거로 사용하지 않는다.

기본 우선순위:

```text
사용자 직접 설정
→ 운영 프로필(잠들기전 교양이)
→ 카테고리 insight
→ 레퍼런스 채널 insight
→ 시스템 기본값
```

레퍼런스 전략이 운영 프로필과 충돌하면 운영 프로필을 우선한다. 예를 들어 강한 공포·충격·확신형 제목은 영성 채널의 참고 패턴일 수 있지만 기본 밤 콘텐츠에 자동 적용하지 않는다.

## 갱신 방식

`sync-insights`는 Markdown을 재귀적으로 발견하고 파일 경로를 NFC로 정규화한다. 각 문서의 SHA-256을 이전 manifest와 비교해 추가·수정·유지·삭제를 집계한다.

새로운 insight는 이후 실행부터 반영한다. 과거 실행은 `editorial_strategy.json`과 `insight_sources.json`에 사용한 insight ID, 파일, 생성일, content hash를 저장하므로 변경되지 않는다.

## 파이프라인 연결

- Phase 4: 주제 분석, 검색어, 후보 도서의 편집·정서 적합성
- Phase 5: 제목, 훅, 감정 흐름, 서사, 결말, 길이
- Phase 6: 문체, 전환, 현실 적용, 마무리
- Phase 7: 책 근거 검증에서 insight를 제외
- Phase 8: 프로필 선택과 적용 전략 미리보기

## 운영 명령

```bash
uv run python scripts/sync_insights.py
uv run python scripts/suggest_topics.py --count 10
```

현재 주제 추천은 insight 편집 적합성을 기준으로 하며 실제 도서 라이브러리의 근거 충분성은 Phase 4 검색을 실행해야 확정된다.
