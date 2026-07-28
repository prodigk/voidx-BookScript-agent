# 프로젝트 작업 현황

## 현재 구현 범위

- Phase 0~3: 로컬 설정, Markdown 진단·청킹, SQLite FTS5, 임베딩·하이브리드 검색
- Phase 4: 주제 분석, 후보 도서 랭킹, 편집 적합성 심사, 근거 큐레이션, 최종 도서 선택
- Phase 5~7: 내러티브 구성안, 출처 연결 대본, 인용·요약·귀속 검증과 리비전
- Phase 7.5~7.6: Editorial Insight 스냅샷과 승인 대본의 Remotion manifest 변환
- Phase 8: FastAPI 작업 API와 Next.js 주제 입력·후보 선택·구성안 편집·대본·검증 UI
- Phase 9: Vercel frontend 배포와 GitHub 기본 브랜치 자동 배포 연결

Production frontend: <https://voidx-bookscript-agent.vercel.app>

## 현재 콘텐츠 방향

새 연구 실행은 인문학·철학·심리학을 핵심 편집 범위로 사용한다. 일상의 감정과 질문에서 시작해 자기이해, 관계, 감정 조절, 삶의 의미와 일상 성찰로 확장한다.

커리어·생산성·조직관리·성과 중심 관점은 요청 스키마에서 기본 제외하며, 주제 기획·편집 전략·후보 도서 심사 프롬프트에도 같은 정책을 적용한다. 과거 실행 산출물과 원본 Markdown은 재현성과 원본 보존 원칙에 따라 수정하지 않는다.

## 실행 구조

```text
Vercel Next.js frontend
        ↓ 브라우저 API 요청
로컬 FastAPI backend
        ↓
로컬 Markdown · SQLite · 생성 outputs
```

Vercel은 공개 frontend만 호스팅한다. Markdown, SQLite, OpenAI API 키와 LLM 호출은 로컬 backend에 남는다.

## 남은 핵심 제한

- 배포된 브라우저에서 `localhost`는 방문자 자신의 컴퓨터를 가리키므로, 로컬 FastAPI 연결에는 안전한 별도 네트워크 방식이 필요하다.
- 작업 취소·자동 재시도와 검증 이슈 단위의 부분 재작성 UI는 아직 없다.
- Remotion은 별도 후속 작업으로 유지하며 문장 단위 자막과 외부 영상 자산은 아직 연결하지 않았다.
- 과거 커리어 주제 실행 산출물은 변경하지 않으며 새 정책은 새 실행부터 적용된다.
