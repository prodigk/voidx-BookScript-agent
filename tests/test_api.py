import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from app.config import BackendSettings, EmbeddingSettings, ProjectSettings, Settings
from app.schemas.topic import TopicRequest
from app.storage.database import connect_database, initialize_database
from backend.app.main import create_app
from backend.app.services.jobs import create_research_job, get_research_job, initialize_job_store


def _successful_runner(settings: Settings, request: TopicRequest) -> Any:
    return SimpleNamespace(status="complete", run_id="generated_run")


def _client(
    tmp_path: Path,
    *,
    api_token: str | None = None,
    research_runner: Any = _successful_runner,
    selection_builder: Any = lambda settings, request: "selection_revision_run",
    narrative_runner: Any = lambda settings, run_id: None,
    revision_builder: Any = lambda settings, request: "narrative_revision_run",
    script_runner: Any = lambda settings, run_id: None,
    validation_runner: Any = lambda settings, run_id: SimpleNamespace(status="approved"),
    citation_revision_builder: Any = lambda settings, run_id, paragraph_ids: "citation_revision_run",
) -> tuple[TestClient, Path, Settings]:
    library = tmp_path / "library"
    library.mkdir(parents=True)
    (library / "책.md").write_text("# 책\n본문", encoding="utf-8")
    output = tmp_path / "outputs"
    run = output / "run_001"
    run.mkdir(parents=True)
    (run / "input.json").write_text(json.dumps({"topic": "테스트 주제"}), encoding="utf-8")
    (run / "script.md").write_text("# 승인 대본", encoding="utf-8")
    (run / "script_with_sources.md").write_text("# 승인 대본\n\n[TYPE:commentary]", encoding="utf-8")
    (run / "citations.json").write_text(json.dumps({
        "status": "approved", "valid_count": 3, "needs_review_count": 0, "invalid_count": 0,
    }), encoding="utf-8")
    (run / "candidate_books.json").write_text(json.dumps([
        {"book_id": "book_1", "title": "책 1", "author": "저자", "source_file": "책1.md", "score": 0.9, "chunk_count": 2, "evidence_chunk_ids": ["chunk_1"], "perspective": "첫 관점", "inclusion_reason": "첫 근거"},
        {"book_id": "book_2", "title": "책 2", "author": "저자", "source_file": "책2.md", "score": 0.8, "chunk_count": 2, "evidence_chunk_ids": ["chunk_2"], "perspective": "둘째 관점", "inclusion_reason": "둘째 근거"},
    ], ensure_ascii=False), encoding="utf-8")
    (run / "evidence.json").write_text(json.dumps([
        {"evidence_id": "ev_1", "book_id": "book_1", "type": "paraphrase", "claim": "근거 1", "source_chunk_ids": ["chunk_1"], "confidence": 0.9},
        {"evidence_id": "ev_2", "book_id": "book_2", "type": "quotation", "claim": "근거 2", "source_chunk_ids": ["chunk_2"], "confidence": 0.8},
    ], ensure_ascii=False), encoding="utf-8")
    (run / "topic_analysis.json").write_text(json.dumps({
        "core_question": "테스트 질문", "intent": "테스트 의도",
        "subtopics": ["하나", "둘"], "keywords": ["하나", "둘", "셋"],
        "search_queries": ["검색 하나", "검색 둘"],
    }, ensure_ascii=False), encoding="utf-8")
    (run / "selected_books.json").write_text(json.dumps({
        "selected_books": [
            {"book_id": "book_1", "role": "첫 관점", "selection_reason": "첫 근거"},
            {"book_id": "book_2", "role": "둘째 관점", "selection_reason": "둘째 근거"},
        ], "excluded_books": [], "cross_book_connection": "첫 관점에서 둘째 관점으로",
    }, ensure_ascii=False), encoding="utf-8")
    sections = [
        {"section_id": "hook", "title": "도입", "narrative_function": "hook", "purpose": "공감", "key_points": ["질문"], "book_ids": [], "evidence_ids": [], "estimated_seconds": 60},
        {"section_id": "problem", "title": "문제", "narrative_function": "problem", "purpose": "문제", "key_points": ["원인"], "book_ids": ["book_1"], "evidence_ids": ["ev_1"], "estimated_seconds": 120},
        {"section_id": "perspective", "title": "관점", "narrative_function": "book_perspective", "purpose": "관점", "key_points": ["전환"], "book_ids": ["book_2"], "evidence_ids": ["ev_2"], "estimated_seconds": 120},
        {"section_id": "integration", "title": "통합", "narrative_function": "integration", "purpose": "통합", "key_points": ["연결"], "book_ids": ["book_1", "book_2"], "evidence_ids": ["ev_1", "ev_2"], "estimated_seconds": 120},
        {"section_id": "conclusion", "title": "결론", "narrative_function": "conclusion", "purpose": "마무리", "key_points": ["여운"], "book_ids": [], "evidence_ids": [], "estimated_seconds": 60},
    ]
    (run / "narrative.json").write_text(json.dumps({
        "title_candidates": ["제목 하나", "제목 둘", "제목 셋"],
        "core_message": "핵심 메시지", "emotional_arc": ["불안", "이해", "안도"],
        "sections": sections, "total_seconds": 480,
    }, ensure_ascii=False), encoding="utf-8")
    database = tmp_path / "data.sqlite"
    initialize_database(database)
    with connect_database(database) as connection:
        connection.execute(
            "INSERT INTO books(id,title,author,category,tags,source_file,content_hash) VALUES(?,?,?,?,?,?,?)",
            ("book_1", "책", "저자", "[]", "[]", "책.md", "hash"),
        )
    settings = Settings(
        project=ProjectSettings(library_path=library, output_path=output, database_path=database),
        embedding=EmbeddingSettings(model="test-model", dimensions=8),
        backend=BackendSettings(
            allowed_origins=["http://localhost:3000"],
            api_token=api_token,
        ),
    )
    return TestClient(create_app(
        settings,
        research_runner=research_runner,
        selection_builder=selection_builder,
        narrative_runner=narrative_runner,
        revision_builder=revision_builder,
        script_runner=script_runner,
        validation_runner=validation_runner,
        citation_revision_builder=citation_revision_builder,
    )), output, settings


def test_health_and_library_status(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)
    assert client.get("/health").json()["status"] == "ok"
    response = client.get("/api/library/status")
    assert response.status_code == 200
    assert response.json()["book_count"] == 1
    assert response.json()["source_file_count"] == 1


def test_local_api_token_protects_api_routes(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path, api_token="local-secret")

    assert client.get("/health").status_code == 200
    assert client.get("/api/library/status").status_code == 401
    response = client.get(
        "/api/library/status",
        headers={"x-local-api-token": "local-secret"},
    )
    assert response.status_code == 200


def test_lists_runs_and_reads_allowlisted_artifact(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)
    listing = client.get("/api/runs").json()
    assert listing["total"] == 1
    assert listing["items"][0]["status"] == "approved"
    detail = client.get("/api/runs/run_001")
    assert detail.json()["validation_valid_count"] == 3
    artifact = client.get("/api/runs/run_001/artifacts/script.md")
    assert artifact.status_code == 200
    assert artifact.text == "# 승인 대본"


def test_blocks_path_traversal_and_non_allowlisted_files(tmp_path: Path) -> None:
    client, output, _ = _client(tmp_path)
    (output / "run_001" / "secret.txt").write_text("secret", encoding="utf-8")
    assert client.get("/api/runs/run_001/artifacts/secret.txt").status_code == 400
    assert client.get("/api/runs/../run_001").status_code in {400, 404}


def test_cors_allows_only_configured_frontend_origin(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)
    response = client.options("/api/runs", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    })
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_creates_and_completes_research_job(tmp_path: Path) -> None:
    received: list[TopicRequest] = []

    def runner(settings: Settings, request: TopicRequest) -> Any:
        received.append(request)
        return SimpleNamespace(status="complete", run_id="generated_run")

    client, _, _ = _client(tmp_path, research_runner=runner)
    response = client.post("/api/research-jobs", json={
        "topic": "타인의 시선에서 자유로워지는 태도",
        "audience": "일반 성인",
        "desired_lenses": ["인문학", "심리학", "생산성"],
    })

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    completed = client.get(f"/api/jobs/{job_id}")
    assert completed.status_code == 200
    assert completed.json()["status"] == "succeeded"
    assert completed.json()["stage"] == "research_complete"
    assert completed.json()["run_id"] == "generated_run"
    assert received[0].audience == "일반 성인"
    assert received[0].desired_lenses == ["인문학", "심리학"]
    assert received[0].excluded_lenses == ["커리어", "생산성", "조직관리", "성과 중심"]
    assert client.get("/api/jobs").json()["total"] == 1


def test_research_api_normalizes_shorts_to_one_minute_and_one_book(tmp_path: Path) -> None:
    received: list[TopicRequest] = []

    def runner(settings: Settings, request: TopicRequest) -> Any:
        received.append(request)
        return SimpleNamespace(status="complete", run_id="shorts_run")

    client, _, _ = _client(tmp_path, research_runner=runner)
    response = client.post("/api/research-jobs", json={
        "topic": "불안할 때 읽을 한 권",
        "content_format": "shorts",
        "duration_minutes": 20,
        "target_book_count": 4,
    })

    assert response.status_code == 202
    assert response.json()["request"]["content_format"] == "shorts"
    assert response.json()["request"]["duration_minutes"] == 1
    assert response.json()["request"]["target_book_count"] == 1
    assert received[0].content_format == "shorts"


def test_records_insufficient_evidence_and_runner_failure(
    tmp_path: Path, monkeypatch: Any,
) -> None:
    def insufficient(settings: Settings, request: TopicRequest) -> Any:
        return SimpleNamespace(status="insufficient_evidence", run_id="evidence_run")

    client, _, _ = _client(tmp_path / "insufficient", research_runner=insufficient)
    created = client.post("/api/research-jobs", json={"topic": "근거가 적은 주제"})
    job = client.get(f"/api/jobs/{created.json()['job_id']}").json()
    assert job["status"] == "succeeded"
    assert job["stage"] == "insufficient_evidence"
    assert job["pipeline_status"] == "insufficient_evidence"

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")

    def failing(settings: Settings, request: TopicRequest) -> Any:
        raise RuntimeError("테스트 실행 실패 sk-test-secret")

    failed_client, _, _ = _client(tmp_path / "failed", research_runner=failing)
    failed = failed_client.post("/api/research-jobs", json={"topic": "실패 확인 주제"})
    failed_job = failed_client.get(f"/api/jobs/{failed.json()['job_id']}").json()
    assert failed_job["status"] == "failed"
    assert failed_job["stage"] == "failed"
    assert failed_job["error"] == "RuntimeError: 테스트 실행 실패 [REDACTED]"


def test_rejects_invalid_or_concurrent_research_jobs(tmp_path: Path) -> None:
    client, _, settings = _client(tmp_path)
    assert client.post("/api/research-jobs", json={"topic": "한"}).status_code == 422

    create_research_job(settings, TopicRequest(topic="이미 대기 중인 작업"))
    response = client.post("/api/research-jobs", json={"topic": "두 번째 연구 작업"})
    assert response.status_code == 409
    assert client.get("/api/jobs/unknown").status_code == 404


def test_marks_interrupted_jobs_failed_when_store_restarts(tmp_path: Path) -> None:
    _, _, settings = _client(tmp_path)
    queued = create_research_job(settings, TopicRequest(topic="중단 복구 테스트"))

    initialize_job_store(settings.project.database_path)

    recovered = get_research_job(settings.project.database_path, queued.job_id)
    assert recovered.status == "failed"
    assert recovered.stage == "interrupted"
    assert recovered.finished_at is not None


def test_creates_selection_revision_and_outline_job(tmp_path: Path) -> None:
    received: list[tuple[list[str], str]] = []

    def builder(settings: Settings, request: Any) -> str:
        received.append((request.selected_book_ids, request.source_run_id))
        return "revised_outline_run"

    narrative_runs: list[str] = []
    client, _, _ = _client(
        tmp_path,
        selection_builder=builder,
        narrative_runner=lambda settings, run_id: narrative_runs.append(run_id),
    )
    response = client.post("/api/runs/run_001/outline-jobs", json={
        "source_run_id": "run_001",
        "selected_book_ids": ["book_2", "book_1"],
    })
    assert response.status_code == 202
    job = client.get(f"/api/jobs/{response.json()['job_id']}").json()
    assert job["kind"] == "outline"
    assert job["status"] == "succeeded"
    assert job["stage"] == "outline_ready"
    assert job["run_id"] == "revised_outline_run"
    assert received == [(["book_2", "book_1"], "run_001")]
    assert narrative_runs == ["revised_outline_run"]


def test_rejects_invalid_outline_selection(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)
    duplicate = client.post("/api/runs/run_001/outline-jobs", json={
        "source_run_id": "run_001", "selected_book_ids": ["book_1", "book_1"],
    })
    assert duplicate.status_code == 422
    unknown = client.post("/api/runs/run_001/outline-jobs", json={
        "source_run_id": "run_001", "selected_book_ids": ["book_1", "missing"],
    })
    assert unknown.status_code == 400
    mismatch = client.post("/api/runs/run_001/outline-jobs", json={
        "source_run_id": "another", "selected_book_ids": ["book_1", "book_2"],
    })
    assert mismatch.status_code == 400


def test_creates_narrative_revision_and_script_job(tmp_path: Path) -> None:
    received: list[tuple[str, str]] = []

    def builder(settings: Settings, request: Any) -> str:
        received.append((request.source_run_id, request.selected_title))
        return "revised_script_run"

    script_runs: list[str] = []
    client, output, _ = _client(
        tmp_path,
        revision_builder=builder,
        script_runner=lambda settings, run_id: script_runs.append(run_id),
    )
    narrative = json.loads((output / "run_001" / "narrative.json").read_text(encoding="utf-8"))
    response = client.post("/api/runs/run_001/script-jobs", json={
        "source_run_id": "run_001", "selected_title": "확정 제목",
        "sections": [
            {"section_id": item["section_id"], "title": item["title"], "purpose": item["purpose"]}
            for item in narrative["sections"]
        ],
    })
    assert response.status_code == 202
    job = client.get(f"/api/jobs/{response.json()['job_id']}").json()
    assert job["kind"] == "script"
    assert job["status"] == "succeeded"
    assert job["stage"] == "script_ready"
    assert job["run_id"] == "revised_script_run"
    assert received == [("run_001", "확정 제목")]
    assert script_runs == ["revised_script_run"]


def test_rejects_script_job_that_moves_hook(tmp_path: Path) -> None:
    client, output, _ = _client(tmp_path)
    narrative = json.loads((output / "run_001" / "narrative.json").read_text(encoding="utf-8"))
    sections = [
        {"section_id": item["section_id"], "title": item["title"], "purpose": item["purpose"]}
        for item in narrative["sections"]
    ]
    sections[0], sections[1] = sections[1], sections[0]
    response = client.post("/api/runs/run_001/script-jobs", json={
        "source_run_id": "run_001", "selected_title": "확정 제목", "sections": sections,
    })
    assert response.status_code == 400
    assert "도입 섹션" in response.json()["detail"]


def test_creates_and_completes_validation_job(tmp_path: Path) -> None:
    received: list[str] = []

    def runner(settings: Settings, run_id: str) -> Any:
        received.append(run_id)
        return SimpleNamespace(status="needs_revision")

    client, output, _ = _client(tmp_path, validation_runner=runner)
    (output / "run_001" / "citations.json").unlink()
    response = client.post("/api/runs/run_001/validation-jobs", json={
        "source_run_id": "run_001",
    })
    assert response.status_code == 202
    job = client.get(f"/api/jobs/{response.json()['job_id']}").json()
    assert job["kind"] == "validation"
    assert job["status"] == "succeeded"
    assert job["stage"] == "validation_needs_revision"
    assert job["pipeline_status"] == "needs_revision"
    assert job["run_id"] == "run_001"
    assert received == ["run_001"]


def test_rejects_missing_or_already_completed_validation(tmp_path: Path) -> None:
    client, output, _ = _client(tmp_path)
    already = client.post("/api/runs/run_001/validation-jobs", json={"source_run_id": "run_001"})
    assert already.status_code == 400
    assert "이미 검증된" in already.json()["detail"]
    (output / "run_001" / "citations.json").unlink()
    (output / "run_001" / "script_with_sources.md").unlink(missing_ok=True)
    missing = client.post("/api/runs/run_001/validation-jobs", json={"source_run_id": "run_001"})
    assert missing.status_code == 400
    assert "필요한 대본" in missing.json()["detail"]


def test_rewrites_selected_paragraphs_and_revalidates_in_one_job(tmp_path: Path) -> None:
    built: list[tuple[str, list[str]]] = []
    validated: list[str] = []

    def builder(settings: Settings, run_id: str, paragraph_ids: list[str]) -> str:
        built.append((run_id, paragraph_ids))
        return "citation_revision_run"

    def validator(settings: Settings, run_id: str) -> Any:
        validated.append(run_id)
        return SimpleNamespace(status="approved")

    client, output, _ = _client(
        tmp_path,
        citation_revision_builder=builder,
        validation_runner=validator,
    )
    (output / "run_001" / "citations.json").write_text(json.dumps({
        "status": "needs_revision",
        "citations": [{
            "citation_id": "citation_001", "paragraph_id": "sec_01_p01",
            "section_id": "sec_01", "text_type": "paraphrase", "text": "기존 문단",
            "book_ids": ["book_1"], "evidence_ids": ["ev_1"], "sources": [],
            "status": "invalid", "confidence": 0.4, "review_summary": "확대 해석",
        }],
        "issues": [{
            "issue_id": "issue_001", "severity": "high",
            "category": "unsupported_paraphrase", "section_id": "sec_01",
            "paragraph_id": "sec_01_p01", "description": "원문보다 확대됐습니다.",
            "recommended_action": "근거 범위로 문장을 완화합니다.", "source_chunk_ids": ["chunk_1"],
        }],
        "valid_count": 0, "needs_review_count": 0, "invalid_count": 1,
    }, ensure_ascii=False), encoding="utf-8")

    response = client.post("/api/runs/run_001/citation-revision-jobs", json={
        "source_run_id": "run_001", "paragraph_ids": ["sec_01_p01"],
    })

    assert response.status_code == 202
    job = client.get(f"/api/jobs/{response.json()['job_id']}").json()
    assert job["kind"] == "citation_revision"
    assert job["status"] == "succeeded"
    assert job["stage"] == "revision_approved"
    assert job["run_id"] == "citation_revision_run"
    assert built == [("run_001", ["sec_01_p01"])]
    assert validated == ["citation_revision_run"]


def test_rejects_citation_revision_without_high_issue(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)
    response = client.post("/api/runs/run_001/citation-revision-jobs", json={
        "source_run_id": "run_001", "paragraph_ids": ["sec_01_p01"],
    })
    assert response.status_code == 400
    assert "수정이 필요한" in response.json()["detail"]
