"""Phase 7 deterministic and semantic citation validation."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from app.agents.phase5 import _read_json, resolve_run_dir
from app.agents.phase6 import _display_title, _load_source_chunks, _plain_markdown
from app.config import Settings
from app.llm.prompt_loader import load_prompt
from app.llm.structured import OpenAIStructuredProvider, StructuredProvider
from app.schemas.evidence import BookSelection, CandidateBook, EvidenceItem
from app.schemas.validation import (
    CitationAssessment,
    CitationRecord,
    CitationReview,
    CitationValidationResult,
    ParsedScriptParagraph,
    SourceReference,
    ValidationIssue,
)

MARKER_PATTERN = re.compile(r"\[([A-Z_]+):([^\]]*)\]")
SECTION_PATTERN = re.compile(r"<!-- REMOTION: section_id=([^ ]+)")


def parse_sourced_script(text: str) -> list[ParsedScriptParagraph]:
    """Parse the deterministic Phase 6 Markdown marker format."""
    paragraphs: list[ParsedScriptParagraph] = []
    section_title = ""
    section_id = ""
    pending: list[str] = []
    section_count = 0
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            if pending and any(item.strip() for item in pending):
                raise ValueError("Unmarked script text before a section boundary")
            section_title = line[3:].strip()
            section_id = ""
            section_count = 0
            pending = []
            in_section = True
            continue
        section_match = SECTION_PATTERN.match(line)
        if section_match:
            section_id = section_match.group(1)
            continue
        if line.startswith("<!--"):
            continue
        if line.startswith("[TYPE:"):
            if not in_section or not section_id:
                raise ValueError("Script paragraph marker is missing section metadata")
            values = {key: value for key, value in MARKER_PATTERN.findall(line)}
            content = "\n".join(pending).strip()
            if not content:
                raise ValueError("Script paragraph marker has no text")
            section_count += 1
            paragraph_id = values.get("PARAGRAPH") or f"{section_id}_p{section_count:02d}"
            paragraphs.append(ParsedScriptParagraph(
                paragraph_id=paragraph_id,
                section_id=section_id,
                section_title=section_title,
                text_type=values["TYPE"],
                text=content,
                book_ids=[item for item in values.get("BOOK", "").split(",") if item],
                evidence_ids=[item for item in values.get("SOURCE", "").split(",") if item],
                chunk_ids=[item for item in values.get("CHUNK", "").split(",") if item],
            ))
            pending = []
            continue
        if in_section:
            pending.append(line)
    if pending and any(item.strip() for item in pending):
        raise ValueError("Unmarked script text at end of file")
    return paragraphs


def _source_reference(chunk: dict[str, object]) -> SourceReference:
    return SourceReference(
        chunk_id=str(chunk["chunk_id"]), book_id=str(chunk["book_id"]), title=str(chunk["title"]),
        author=str(chunk["author"]), source_file=str(chunk["source_file"]),
        heading_path=[str(item) for item in chunk["heading_path"]],
        start_line=int(chunk["start_line"]), end_line=int(chunk["end_line"]),
        content_hash=str(chunk["content_hash"]),
    )


def _issue(
    issues: list[ValidationIssue], paragraph: ParsedScriptParagraph, category: str,
    description: str, action: str, *, severity: str = "high",
) -> None:
    issues.append(ValidationIssue.model_validate({
        "issue_id": f"issue_{len(issues) + 1:03d}", "severity": severity, "category": category,
        "section_id": paragraph.section_id, "paragraph_id": paragraph.paragraph_id,
        "description": description, "recommended_action": action,
        "source_chunk_ids": paragraph.chunk_ids,
    }))


def _check_source_file(settings: Settings, chunk: dict[str, object]) -> bool:
    root = settings.project.library_path.resolve()
    path = (root / str(chunk["source_file"])).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return False
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    start, end = int(chunk["start_line"]), int(chunk["end_line"])
    if start < 1 or end < start or end > len(lines):
        return False
    source_range = "\n".join(lines[start - 1:end])
    return _plain_markdown(str(chunk["content"])) in _plain_markdown(source_range)


def _report_markdown(result: CitationValidationResult) -> str:
    status = "수정 필요" if result.status == "needs_revision" else "승인"
    lines = [
        "# 대본 출처 검증 리포트", "", f"- 상태: **{status}**",
        f"- 유효: {result.valid_count}", f"- 검토 필요: {result.needs_review_count}",
        f"- 무효: {result.invalid_count}", "", "## 검증 문제",
    ]
    if not result.issues:
        lines.append("- 발견된 문제가 없습니다.")
    for issue in result.issues:
        lines += [
            "", f"### {issue.issue_id} · {issue.severity.upper()} · {issue.category}",
            f"- 위치: {issue.section_id} / {issue.paragraph_id}", f"- 문제: {issue.description}",
            f"- 권장 조치: {issue.recommended_action}",
        ]
    lines += ["", "## 인용별 결과"]
    for citation in result.citations:
        sources = ", ".join(
            f"{item.source_file}:{item.start_line}-{item.end_line}" for item in citation.sources
        )
        lines += [
            "", f"### {citation.citation_id} · {citation.status}",
            f"- 섹션: {citation.section_id}", f"- 유형: {citation.text_type}",
            f"- 출처: {sources}", f"- 검토: {citation.review_summary}",
        ]
    return "\n".join(lines) + "\n"


def validate_script_run(
    settings: Settings,
    run_id: str,
    *,
    structured: StructuredProvider | None = None,
    source_chunks: list[dict[str, object]] | None = None,
) -> CitationValidationResult:
    """Validate a Phase 6 run and write citations and approval artifacts."""
    run_dir = resolve_run_dir(settings.project.output_path, run_id)
    citations_path, report_path = run_dir / "citations.json", run_dir / "validation_report.md"
    if citations_path.exists() or report_path.exists():
        raise FileExistsError("Validation artifacts already exist; refusing to overwrite the run")
    paragraphs = parse_sourced_script((run_dir / "script_with_sources.md").read_text(encoding="utf-8"))
    grounded = [item for item in paragraphs if item.evidence_ids or item.chunk_ids or item.book_ids]
    evidence = [EvidenceItem.model_validate(item) for item in _read_json(run_dir / "evidence.json")]
    evidence_by_id = {item.evidence_id: item for item in evidence}
    candidates = [CandidateBook.model_validate(item) for item in _read_json(run_dir / "candidate_books.json")]
    candidate_by_id = {item.book_id: item for item in candidates}
    selected = BookSelection.model_validate(_read_json(run_dir / "selected_books.json"))
    required_chunks = {item for paragraph in grounded for item in paragraph.chunk_ids}
    source_chunks = source_chunks if source_chunks is not None else _load_source_chunks(
        settings.project.database_path, required_chunks,
    )
    source_by_id = {str(item["chunk_id"]): item for item in source_chunks}
    issues: list[ValidationIssue] = []
    deterministic_invalid: set[str] = set()
    for paragraph in grounded:
        expected_chunks: set[str] = set()
        expected_books: set[str] = set()
        missing_evidence = [item for item in paragraph.evidence_ids if item not in evidence_by_id]
        if missing_evidence:
            _issue(issues, paragraph, "missing_source", "대본의 evidence ID를 찾을 수 없습니다.", "근거 ID를 다시 연결합니다.")
            deterministic_invalid.add(paragraph.paragraph_id)
            continue
        for evidence_id in paragraph.evidence_ids:
            evidence_item = evidence_by_id[evidence_id]
            expected_chunks.update(evidence_item.source_chunk_ids)
            expected_books.add(evidence_item.book_id)
        if expected_chunks != set(paragraph.chunk_ids) or expected_books != set(paragraph.book_ids):
            _issue(issues, paragraph, "mixed_book_attribution", "책·근거·청크 마커의 귀속이 일치하지 않습니다.", "마커를 evidence 데이터와 일치시킵니다.")
            deterministic_invalid.add(paragraph.paragraph_id)
        for chunk_id in paragraph.chunk_ids:
            chunk = source_by_id.get(chunk_id)
            if chunk is None:
                _issue(issues, paragraph, "missing_source", f"청크를 찾을 수 없습니다: {chunk_id}", "인덱스를 갱신하고 출처를 다시 연결합니다.")
                deterministic_invalid.add(paragraph.paragraph_id)
                continue
            if hashlib.sha256(str(chunk["content"]).encode("utf-8")).hexdigest() != str(chunk["content_hash"]):
                _issue(issues, paragraph, "missing_source", f"청크 해시가 일치하지 않습니다: {chunk_id}", "인덱스를 재구축합니다.")
                deterministic_invalid.add(paragraph.paragraph_id)
            if not _check_source_file(settings, chunk):
                _issue(issues, paragraph, "invalid_line_range", f"원본 파일과 행 범위를 확인할 수 없습니다: {chunk_id}", "라이브러리 인덱스를 갱신하고 행 범위를 다시 계산합니다.")
                deterministic_invalid.add(paragraph.paragraph_id)
        if paragraph.text_type == "quotation":
            source_text = "\n".join(str(source_by_id[item]["content"]) for item in paragraph.chunk_ids if item in source_by_id)
            if _plain_markdown(paragraph.text) not in _plain_markdown(source_text):
                _issue(issues, paragraph, "modified_quotation", "직접 인용문이 원문과 일치하지 않습니다.", "원문의 문구를 그대로 사용합니다.")
                deterministic_invalid.add(paragraph.paragraph_id)
    title_line = paragraphs[-1].text if paragraphs else ""
    for item in selected.selected_books:
        title = _display_title(candidate_by_id[item.book_id].title)
        if f"『{title}』" not in title_line:
            _issue(issues, paragraphs[-1], "incorrect_title", f"최종 참고 도서 표기에서 제목을 확인할 수 없습니다: {title}", "선정 도서 제목을 정확히 표기합니다.")
            deterministic_invalid.add(paragraphs[-1].paragraph_id)
    review_input = []
    for paragraph in grounded:
        review_input.append({
            "paragraph": paragraph.model_dump(mode="json"),
            "evidence": [evidence_by_id[item].model_dump(mode="json") for item in paragraph.evidence_ids if item in evidence_by_id],
            "sources": [source_by_id[item] for item in paragraph.chunk_ids if item in source_by_id],
        })
    if structured is None:
        llm_settings = settings.llm.model_copy(update={"max_output_tokens": settings.script.max_output_tokens})
        structured = OpenAIStructuredProvider(llm_settings)
    review = structured.parse(
        stage="citation_reviewer", instructions=load_prompt("citation_reviewer"),
        input_text=json.dumps(review_input, ensure_ascii=False), output_type=CitationReview,
    )
    assessment_by_id = {item.paragraph_id: item for item in review.assessments}
    expected_ids = {item.paragraph_id for item in grounded}
    if set(assessment_by_id) != expected_ids or len(review.assessments) != len(expected_ids):
        raise ValueError("Citation review must assess every grounded paragraph exactly once")
    citations: list[CitationRecord] = []
    for index, paragraph in enumerate(grounded, 1):
        assessment: CitationAssessment = assessment_by_id[paragraph.paragraph_id]
        if not assessment.supported:
            categories = assessment.issue_categories or ["unsupported_paraphrase"]
            for category in categories:
                _issue(
                    issues, paragraph, category, assessment.explanation,
                    assessment.suggested_rewrite or "근거 범위 안에서 문장을 완화하거나 다시 작성합니다.",
                )
        invalid = paragraph.paragraph_id in deterministic_invalid or not assessment.supported
        status = "invalid" if invalid else ("needs_review" if assessment.confidence < 0.7 else "valid")
        citations.append(CitationRecord(
            citation_id=f"citation_{index:03d}", paragraph_id=paragraph.paragraph_id,
            section_id=paragraph.section_id, text_type=paragraph.text_type, text=paragraph.text,
            book_ids=paragraph.book_ids, evidence_ids=paragraph.evidence_ids,
            sources=[_source_reference(source_by_id[item]) for item in paragraph.chunk_ids if item in source_by_id],
            status=status, confidence=assessment.confidence, review_summary=assessment.explanation,
        ))
    invalid_count = sum(item.status == "invalid" for item in citations)
    needs_review_count = sum(item.status == "needs_review" for item in citations)
    result = CitationValidationResult(
        status="needs_revision" if any(item.severity == "high" for item in issues) else "approved",
        citations=citations, issues=issues,
        valid_count=len(citations) - invalid_count - needs_review_count,
        needs_review_count=needs_review_count, invalid_count=invalid_count,
    )
    citations_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(_report_markdown(result), encoding="utf-8")
    return result


def create_validated_revision(settings: Settings, source_run_id: str) -> str:
    """Create a new run with only invalid citation paragraphs replaced by reviewed rewrites."""
    source = resolve_run_dir(settings.project.output_path, source_run_id)
    result = CitationValidationResult.model_validate(_read_json(source / "citations.json"))
    if result.status != "needs_revision":
        raise ValueError("Validation result does not require revision")
    replacements: dict[str, str] = {}
    citations = {item.paragraph_id: item for item in result.citations}
    for issue in result.issues:
        if issue.severity != "high" or issue.paragraph_id not in citations:
            continue
        previous = replacements.get(issue.paragraph_id)
        if previous and previous != issue.recommended_action:
            raise ValueError(f"Conflicting revisions for paragraph: {issue.paragraph_id}")
        replacements[issue.paragraph_id] = issue.recommended_action
    if not replacements:
        raise ValueError("No targeted revisions are available")
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_citation-revision"
    destination = settings.project.output_path / run_id
    destination.mkdir(parents=True, exist_ok=False)
    for path in source.iterdir():
        if path.is_file() and path.name not in {"citations.json", "validation_report.md"}:
            shutil.copy2(path, destination / path.name)
    sourced_path, clean_path = destination / "script_with_sources.md", destination / "script.md"
    sourced = sourced_path.read_text(encoding="utf-8")
    clean = clean_path.read_text(encoding="utf-8")
    for paragraph_id, replacement in replacements.items():
        original = citations[paragraph_id].text
        sourced_anchor = f"\n{original}\n\n[TYPE:"
        if sourced_anchor not in sourced:
            raise ValueError(f"Could not locate sourced paragraph: {paragraph_id}")
        sourced = sourced.replace(sourced_anchor, f"\n{replacement}\n\n[TYPE:", 1)
        clean_anchor = f"\n{original}\n"
        if clean_anchor not in clean:
            raise ValueError(f"Could not locate clean paragraph: {paragraph_id}")
        clean = clean.replace(clean_anchor, f"\n{replacement}\n", 1)
    sourced_path.write_text(sourced, encoding="utf-8")
    clean_path.write_text(clean, encoding="utf-8")
    return run_id
