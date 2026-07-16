"""Phase 6 evidence-grounded Korean narration script generation."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Sequence
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from app.agents.phase5 import _read_json, resolve_run_dir
from app.config import Settings
from app.llm.prompt_loader import load_prompt
from app.llm.structured import OpenAIStructuredProvider, StructuredProvider
from app.schemas.evidence import BookSelection, CandidateBook, EvidenceItem
from app.schemas.insight import EditorialStrategy
from app.schemas.narrative import NarrativePlan
from app.schemas.script import ScriptDocument, ScriptParagraph
from app.schemas.topic import TopicRequest
from app.storage.database import connect_database


def _plain_markdown(text: str) -> str:
    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"(?m)^\s*[-–—>]\s*", "", text)
    return " ".join(text.split())


def _verified_quote_text(
    evidence_item: EvidenceItem,
    source_by_id: dict[str, dict[str, object]],
) -> str | None:
    """Return exact source wording for a quotation claim, including a conservative near-match."""
    source_text = "\n".join(
        str(source_by_id[chunk_id]["content"]) for chunk_id in evidence_item.source_chunk_ids
    )
    if _plain_markdown(evidence_item.claim) in _plain_markdown(source_text):
        return evidence_item.claim

    candidates: list[str] = []
    for line in source_text.splitlines():
        line = line.strip()
        if not line:
            continue
        candidates.extend(part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", line))
    claim = _plain_markdown(evidence_item.claim)
    viable = [item for item in candidates if 15 <= len(_plain_markdown(item)) <= 300]
    if not viable:
        return None
    best = max(viable, key=lambda item: SequenceMatcher(None, claim, _plain_markdown(item)).ratio())
    similarity = SequenceMatcher(None, claim, _plain_markdown(best)).ratio()
    return best if similarity >= 0.72 else None


def _display_title(title: str) -> str:
    return title.lstrip("@ ").rstrip(". ")


def _repair_quotations(
    script: ScriptDocument,
    evidence: Sequence[EvidenceItem],
    source_chunks: Sequence[dict[str, object]],
) -> ScriptDocument:
    """Replace model-copied quotations with the exact, source-checked evidence text."""
    evidence_by_id = {item.evidence_id: item for item in evidence}
    source_by_id = {str(item["chunk_id"]): item for item in source_chunks}
    repaired_sections = []
    for section in script.sections:
        repaired_paragraphs = []
        repaired_quote: tuple[str, str] | None = None
        for paragraph in section.paragraphs:
            if paragraph.text_type in {"paraphrase", "interpretation"} and not paragraph.evidence_ids:
                repaired_paragraphs.append(paragraph.model_copy(update={"text_type": "commentary"}))
                continue
            if paragraph.text_type != "quotation" or len(paragraph.evidence_ids) != 1:
                repaired_paragraphs.append(paragraph)
                continue
            evidence_id = paragraph.evidence_ids[0]
            evidence_item = evidence_by_id.get(evidence_id)
            if evidence_item is None or evidence_item.type != "quotation":
                repaired_paragraphs.append(paragraph)
                continue
            quote_text = _verified_quote_text(evidence_item, source_by_id)
            if quote_text is None:
                repaired_paragraphs.append(paragraph.model_copy(update={
                    "text": evidence_item.claim, "text_type": "paraphrase",
                }))
                continue
            repaired_paragraphs.append(paragraph.model_copy(update={"text": quote_text}))
            repaired_quote = evidence_id, quote_text
        cue = section.remotion_cue
        if cue.scene_type == "quote_card" and repaired_quote:
            evidence_id, quote_text = repaired_quote
            cue = cue.model_copy(update={"quote_evidence_id": evidence_id, "quote_text": quote_text})
        elif cue.scene_type == "quote_card":
            cue = cue.model_copy(update={
                "scene_type": "standard", "quote_text": None,
                "quote_evidence_id": None, "quote_duration_seconds": None,
            })
        repaired_sections.append(section.model_copy(update={"paragraphs": repaired_paragraphs, "remotion_cue": cue}))
    return script.model_copy(update={"sections": repaired_sections})


def _ensure_quote_card(
    script: ScriptDocument,
    narrative: NarrativePlan,
    evidence: Sequence[EvidenceItem],
    source_chunks: Sequence[dict[str, object]],
) -> ScriptDocument:
    """Insert one exact, locally verified quote card when the model omitted all of them."""
    if any(section.remotion_cue.scene_type == "quote_card" for section in script.sections):
        return script

    evidence_by_id = {item.evidence_id: item for item in evidence}
    source_by_id = {str(item["chunk_id"]): item for item in source_chunks}
    narrative_by_id = {section.section_id: section for section in narrative.sections}
    used_paragraph_ids = {
        paragraph.paragraph_id for section in script.sections for paragraph in section.paragraphs
    }
    repaired_sections = []
    inserted = False
    for section in script.sections:
        if inserted:
            repaired_sections.append(section)
            continue
        narrative_section = narrative_by_id[section.section_id]
        quote_pair = next((
            (evidence_by_id[evidence_id], quote_text)
            for evidence_id in narrative_section.evidence_ids
            if evidence_id in evidence_by_id
            and evidence_by_id[evidence_id].type == "quotation"
            for quote_text in [_verified_quote_text(evidence_by_id[evidence_id], source_by_id)]
            if quote_text is not None
        ), None)
        if quote_pair is None:
            repaired_sections.append(section)
            continue
        quote, quote_text = quote_pair

        paragraph_id = f"quote_{section.section_id}"
        suffix = 2
        while paragraph_id in used_paragraph_ids:
            paragraph_id = f"quote_{section.section_id}_{suffix}"
            suffix += 1
        quote_paragraph = ScriptParagraph(
            paragraph_id=paragraph_id,
            text_type="quotation",
            text=quote_text,
            book_ids=[quote.book_id],
            evidence_ids=[quote.evidence_id],
        )
        cue = section.remotion_cue.model_copy(update={
            "scene_type": "quote_card",
            "quote_text": quote_text,
            "quote_evidence_id": quote.evidence_id,
            "quote_duration_seconds": 8,
        })
        repaired_sections.append(section.model_copy(update={
            "paragraphs": [*section.paragraphs, quote_paragraph],
            "remotion_cue": cue,
        }))
        inserted = True
    return script.model_copy(update={"sections": repaired_sections})


def _load_source_chunks(database_path: Path, chunk_ids: set[str]) -> list[dict[str, object]]:
    if not chunk_ids:
        return []
    placeholders = ",".join("?" for _ in chunk_ids)
    with connect_database(database_path) as connection:
        rows = connection.execute(
            f"""
            SELECT c.id AS chunk_id, c.book_id, b.title, b.author, b.source_file,
                   c.heading_path, c.start_line, c.end_line, c.content, c.content_hash
            FROM chunks c JOIN books b ON b.id = c.book_id
            WHERE c.id IN ({placeholders})
            """,
            sorted(chunk_ids),
        ).fetchall()
    found = {row["chunk_id"] for row in rows}
    missing = chunk_ids - found
    if missing:
        raise ValueError(f"Source chunks missing from index: {', '.join(sorted(missing))}")
    return [
        {
            "chunk_id": row["chunk_id"], "book_id": row["book_id"], "title": row["title"],
            "author": row["author"], "source_file": row["source_file"],
            "heading_path": json.loads(row["heading_path"]), "start_line": row["start_line"],
            "end_line": row["end_line"], "content": row["content"], "content_hash": row["content_hash"],
        }
        for row in rows
    ]


def _validate_script(
    script: ScriptDocument,
    narrative: NarrativePlan,
    selected: BookSelection,
    evidence: Sequence[EvidenceItem],
    source_chunks: Sequence[dict[str, object]],
    *,
    characters_per_minute: int,
    length_tolerance: float,
) -> None:
    if script.target_duration_seconds != narrative.total_seconds:
        raise ValueError("Script duration does not match narrative duration")
    if [item.section_id for item in script.sections] != [item.section_id for item in narrative.sections]:
        raise ValueError("Script sections must preserve narrative order and IDs")
    selected_ids = {item.book_id for item in selected.selected_books}
    evidence_by_id = {item.evidence_id: item for item in evidence}
    source_by_id = {str(item["chunk_id"]): item for item in source_chunks}
    paragraph_ids: set[str] = set()
    quote_scenes = 0
    for script_section, narrative_section in zip(script.sections, narrative.sections, strict=True):
        if script_section.estimated_seconds != narrative_section.estimated_seconds:
            raise ValueError(f"Section duration changed: {script_section.section_id}")
        section_evidence: set[str] = set()
        quote_paragraphs = []
        for paragraph in script_section.paragraphs:
            if paragraph.paragraph_id in paragraph_ids:
                raise ValueError(f"Duplicate paragraph ID: {paragraph.paragraph_id}")
            paragraph_ids.add(paragraph.paragraph_id)
            book_ids = set(paragraph.book_ids)
            evidence_ids = set(paragraph.evidence_ids)
            if not book_ids <= selected_ids or not book_ids <= set(narrative_section.book_ids):
                raise ValueError(f"Invalid book attribution: {paragraph.paragraph_id}")
            if not evidence_ids <= evidence_by_id.keys() or not evidence_ids <= set(narrative_section.evidence_ids):
                raise ValueError(f"Invalid evidence attribution: {paragraph.paragraph_id}")
            evidence_books = {evidence_by_id[item].book_id for item in evidence_ids}
            if evidence_books != book_ids and evidence_ids:
                raise ValueError(f"Evidence/book mismatch: {paragraph.paragraph_id}")
            if paragraph.text_type in {"quotation", "paraphrase", "interpretation"} and not evidence_ids:
                raise ValueError(f"Book-related paragraph has no evidence: {paragraph.paragraph_id}")
            if paragraph.text_type == "quotation":
                if len(evidence_ids) != 1 or len(book_ids) != 1:
                    raise ValueError(f"Quotation must have one source: {paragraph.paragraph_id}")
                evidence_item = evidence_by_id[next(iter(evidence_ids))]
                if evidence_item.type != "quotation":
                    raise ValueError(f"Quotation uses non-quotation evidence: {paragraph.paragraph_id}")
                source_text = "\n".join(
                    str(source_by_id[item]["content"]) for item in evidence_item.source_chunk_ids
                )
                if _plain_markdown(paragraph.text) not in _plain_markdown(source_text):
                    raise ValueError(f"Quotation is not an exact source substring: {paragraph.paragraph_id}")
                quote_paragraphs.append(paragraph)
            section_evidence.update(evidence_ids)
        if not set(narrative_section.evidence_ids) <= section_evidence:
            raise ValueError(f"Narrative evidence omitted from script section: {script_section.section_id}")
        cue = script_section.remotion_cue
        if cue.scene_type == "quote_card":
            quote_scenes += 1
            if (
                len(quote_paragraphs) != 1 or not cue.quote_text or not cue.quote_evidence_id
                or cue.quote_duration_seconds is None
            ):
                raise ValueError(f"Quote card must contain one quotation: {script_section.section_id}")
            quote = quote_paragraphs[0]
            if cue.quote_evidence_id not in quote.evidence_ids or _plain_markdown(cue.quote_text) != _plain_markdown(quote.text):
                raise ValueError(f"Quote card text/source mismatch: {script_section.section_id}")
        elif quote_paragraphs or cue.quote_text or cue.quote_evidence_id or cue.quote_duration_seconds:
            raise ValueError(f"Quotation must use a quote card: {script_section.section_id}")
    if not 1 <= quote_scenes <= 2:
        raise ValueError("Script must contain one or two quote-card scenes")
    text_length = sum(len(paragraph.text) for section in script.sections for paragraph in section.paragraphs)
    target = round(narrative.total_seconds / 60 * characters_per_minute)
    minimum, maximum = target * (1 - length_tolerance), target * (1 + length_tolerance)
    if not minimum <= text_length <= maximum:
        raise ValueError(f"Script length {text_length} is outside target range {minimum:.0f}-{maximum:.0f}")


def _render_scripts(
    script: ScriptDocument,
    evidence: Sequence[EvidenceItem],
    candidates: Sequence[CandidateBook],
    selected: BookSelection,
    source_chunks: Sequence[dict[str, object]],
    *,
    renderer: str,
    fps: int,
) -> tuple[str, str]:
    evidence_by_id = {item.evidence_id: item for item in evidence}
    candidate_by_id = {item.book_id: item for item in candidates}
    source_by_id = {str(item["chunk_id"]): item for item in source_chunks}
    sourced = [
        f"# {script.title}", "", f"- 예상 길이: {script.target_duration_seconds // 60}분",
        f"- 영상 렌더러: {renderer}", f"- 기준 FPS: {fps}", "",
    ]
    clean = [f"# {script.title}", ""]
    elapsed = 0
    for section in script.sections:
        start, end = elapsed, elapsed + section.estimated_seconds
        elapsed = end
        sourced += [
            f"## {section.title}", "",
            f"<!-- REMOTION: section_id={section.section_id} start={start}s end={end}s fps={fps} -->",
            f"<!-- VISUAL: {section.remotion_cue.visual_intent} -->",
            f"<!-- ON_SCREEN_TEXT: {' | '.join(section.remotion_cue.on_screen_text)} -->",
            f"<!-- ASSETS: {' | '.join(section.remotion_cue.suggested_assets)} -->", "",
        ]
        if section.remotion_cue.scene_type == "quote_card":
            evidence_item = evidence_by_id[section.remotion_cue.quote_evidence_id or ""]
            source = source_by_id[evidence_item.source_chunk_ids[0]]
            title = _display_title(candidate_by_id[evidence_item.book_id].title)
            sourced += [
                f"<!-- QUOTE_SCENE: duration={section.remotion_cue.quote_duration_seconds}s -->",
                f"<!-- QUOTE_TEXT: {section.remotion_cue.quote_text} -->",
                f"<!-- QUOTE_SOURCE: {title} | {source['source_file']}:{source['start_line']}-{source['end_line']} -->",
                "",
            ]
        clean += [f"## {section.title}", ""]
        for paragraph in section.paragraphs:
            evidence_ids = paragraph.evidence_ids
            chunk_ids = list(dict.fromkeys(
                chunk_id for evidence_id in evidence_ids
                for chunk_id in evidence_by_id[evidence_id].source_chunk_ids
            ))
            sourced += [paragraph.text, ""]
            markers = [f"TYPE:{paragraph.text_type}", f"PARAGRAPH:{paragraph.paragraph_id}"]
            if paragraph.book_ids:
                markers.append("BOOK:" + ",".join(paragraph.book_ids))
            if evidence_ids:
                markers.append("SOURCE:" + ",".join(evidence_ids))
                markers.append("CHUNK:" + ",".join(chunk_ids))
            sourced += ["[" + "] [".join(markers) + "]", ""]
            clean += [paragraph.text, ""]
    titles = [_display_title(candidate_by_id[item.book_id].title) for item in selected.selected_books]
    if len(titles) == 2:
        title_list = f"『{titles[0]}』와 『{titles[1]}』"
    else:
        title_list = ", ".join(f"『{title}』" for title in titles[:-1]) + f", 그리고 『{titles[-1]}』"
    attribution = f"이 영상은 {title_list}의 내용을 바탕으로 구성되었습니다."
    sourced += [attribution, "", "[TYPE:commentary]"]
    clean += [attribution]
    return "\n".join(sourced).rstrip() + "\n", "\n".join(clean).rstrip() + "\n"


def generate_script(
    settings: Settings,
    run_id: str,
    *,
    structured: StructuredProvider | None = None,
    source_chunks: list[dict[str, object]] | None = None,
) -> ScriptDocument:
    """Generate validated internal and clean scripts for a completed Phase 5 run."""
    run_dir = resolve_run_dir(settings.project.output_path, run_id)
    sourced_path, clean_path = run_dir / "script_with_sources.md", run_dir / "script.md"
    if sourced_path.exists() or clean_path.exists():
        raise FileExistsError("Script artifacts already exist; refusing to overwrite the run")
    request = TopicRequest.model_validate(_read_json(run_dir / "input.json"))
    narrative = NarrativePlan.model_validate(_read_json(run_dir / "narrative.json"))
    candidates = [CandidateBook.model_validate(item) for item in _read_json(run_dir / "candidate_books.json")]
    selected = BookSelection.model_validate(_read_json(run_dir / "selected_books.json"))
    strategy_data = _read_json(run_dir / "editorial_strategy.json") if (run_dir / "editorial_strategy.json").is_file() else None
    editorial_strategy = EditorialStrategy.model_validate(strategy_data) if strategy_data and "profile" in strategy_data else None
    selected_ids = {item.book_id for item in selected.selected_books}
    evidence = [
        EvidenceItem.model_validate(item) for item in _read_json(run_dir / "evidence.json")
        if item["book_id"] in selected_ids
    ]
    evidence_by_id = {item.evidence_id: item for item in evidence}
    required_evidence = {item for section in narrative.sections for item in section.evidence_ids}
    if not required_evidence <= evidence_by_id.keys():
        raise ValueError("Narrative references evidence missing from Phase 4 artifacts")
    required_chunks = {
        chunk_id for evidence_id in required_evidence
        for chunk_id in evidence_by_id[evidence_id].source_chunk_ids
    }
    source_chunks = source_chunks if source_chunks is not None else _load_source_chunks(
        settings.project.database_path, required_chunks,
    )
    if {str(item["chunk_id"]) for item in source_chunks} != required_chunks:
        raise ValueError("Supplied source chunks do not exactly match narrative evidence")
    candidate_by_id = {item.book_id: item for item in candidates}
    restricted_names = {
        value for item in selected.selected_books
        for value in (_display_title(candidate_by_id[item.book_id].title), candidate_by_id[item.book_id].author)
        if value and value != "unknown"
    }
    source_by_id = {str(item["chunk_id"]): item for item in source_chunks}
    verified_quote_candidates = []
    for item in evidence:
        if item.type != "quotation" or item.evidence_id not in required_evidence:
            continue
        quote_text = _verified_quote_text(item, source_by_id)
        if quote_text is not None:
            verified_quote_candidates.append({"evidence_id": item.evidence_id, "quote_text": quote_text})
    context = {
        "request": request.model_dump(mode="json"),
        "characters_per_minute": settings.script.characters_per_minute,
        "narrative": narrative.model_dump(mode="json"),
        "selected_books": [
            {**item.model_dump(mode="json"), "title": candidate_by_id[item.book_id].title,
             "author": candidate_by_id[item.book_id].author}
            for item in selected.selected_books
        ],
        "evidence": [evidence_by_id[item].model_dump(mode="json") for item in sorted(required_evidence)],
        "verified_quote_candidates": verified_quote_candidates,
        "editorial_strategy": editorial_strategy.model_dump(mode="json") if editorial_strategy else None,
        "source_chunks": source_chunks,
    }
    if structured is None:
        llm_settings = settings.llm.model_copy(update={"max_output_tokens": settings.script.max_output_tokens})
        structured = OpenAIStructuredProvider(llm_settings)
    script = structured.parse(
        stage="script_writer", instructions=load_prompt("script_writer"),
        input_text=json.dumps(context, ensure_ascii=False), output_type=ScriptDocument,
    )
    if narrative.selected_title:
        script = script.model_copy(update={"title": narrative.selected_title})
    script = _repair_quotations(script, evidence, source_chunks)
    script = _ensure_quote_card(script, narrative, evidence, source_chunks)
    _validate_script(
        script, narrative, selected, evidence, source_chunks,
        characters_per_minute=settings.script.characters_per_minute,
        length_tolerance=settings.script.length_tolerance,
    )
    for paragraph in (item for section in script.sections for item in section.paragraphs):
        if any(name in paragraph.text for name in restricted_names):
            raise ValueError(f"Book title/author exposed before final attribution: {paragraph.paragraph_id}")
    sourced, clean = _render_scripts(
        script, evidence, candidates, selected, source_chunks,
        renderer=settings.video.primary_renderer, fps=settings.video.fps,
    )
    sourced_path.write_text(sourced, encoding="utf-8")
    clean_path.write_text(clean, encoding="utf-8")
    return script


def create_script_revision(settings: Settings, source_run_id: str) -> str:
    """Copy pre-script artifacts into a new immutable run for a script revision."""
    source = resolve_run_dir(settings.project.output_path, source_run_id)
    request = TopicRequest.model_validate(_read_json(source / "input.json"))
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", request.topic).strip("-")[:60]
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{slug}-script-revision"
    destination = settings.project.output_path / run_id
    destination.mkdir(parents=True, exist_ok=False)
    downstream_artifacts = {
        "script.md", "script_with_sources.md", "citations.json", "validation_report.md",
    }
    for path in source.iterdir():
        if path.is_file() and path.name not in downstream_artifacts:
            shutil.copy2(path, destination / path.name)
    return run_id
