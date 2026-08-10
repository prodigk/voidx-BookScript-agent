"use client";

import {useMemo, useState} from "react";
import {ArrowDown, ArrowUp, Clock3, FileText, GripVertical, Quote, Sparkles} from "lucide-react";

import type {CandidateBook, NarrativePlan, NarrativeSection, SelectionArtifact} from "@/types/api";

const FUNCTION_LABELS: Record<string, string> = {
  hook: "도입", problem: "문제 제기", book_intro: "책 소개", book_perspective: "책의 관점", transition: "전환",
  tension: "긴장", integration: "통합", application: "적용", conclusion: "마무리",
};

type Props = {
  plan: NarrativePlan;
  selection: SelectionArtifact;
  candidates: CandidateBook[];
  busy?: boolean;
  onGenerateScript: (payload: {selected_title: string; sections: {section_id: string; title: string; purpose: string}[]}) => Promise<void>;
};

export function OutlineResult({plan, selection, candidates, busy = false, onGenerateScript}: Props) {
  const [selectedTitle, setSelectedTitle] = useState(plan.selected_title ?? plan.title_candidates[0] ?? "");
  const [sections, setSections] = useState(plan.sections);
  const titleById = useMemo(() => new Map(candidates.map((book) => [book.book_id, book.title])), [candidates]);

  const updateSection = (sectionId: string, field: "title" | "purpose", value: string) => {
    setSections((current) => current.map((section) => section.section_id === sectionId ? {...section, [field]: value} : section));
  };
  const moveSection = (index: number, direction: -1 | 1) => {
    const nextIndex = index + direction;
    if (index <= 0 || index >= sections.length - 1 || nextIndex <= 0 || nextIndex >= sections.length - 1) return;
    setSections((current) => {
      const next = [...current];
      [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
      return next;
    });
  };
  const valid = selectedTitle.trim().length > 0 && sections.every((section) => section.title.trim() && section.purpose.trim());

  return (
    <section className="workspace-card mt-6 p-5 sm:p-7 lg:p-8" aria-labelledby="outline-title">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="eyebrow">Narrative architecture</p><h2 id="outline-title" className="mt-2 text-[22px] font-semibold tracking-[-0.02em]">영상 구성안 편집</h2><p className="mt-2 text-sm leading-6 text-muted">근거 연결은 유지한 채 제목과 이야기의 표현·순서를 다듬으세요.</p></div>
        <span className="selection-count inline-flex items-center gap-1.5"><Clock3 size={14} aria-hidden="true" /> {Math.floor(plan.total_seconds / 60)}분 {plan.total_seconds % 60}초</span>
      </div>

      <div className="outline-summary mt-6">
        <div><p className="eyebrow">Core message</p><p className="mt-3 text-base font-medium leading-7 text-ink">{plan.core_message}</p></div>
        <div className="mt-5 border-t border-hairline-soft pt-5"><p className="text-xs font-semibold text-muted">감정 흐름</p><div className="mt-3 flex flex-wrap items-center gap-2">{plan.emotional_arc.map((item, index) => <span key={`${item}-${index}`} className="arc-chip">{item}</span>)}</div></div>
      </div>

      <fieldset className="mt-7">
        <legend className="flex items-center gap-2 font-semibold"><Quote size={17} className="text-primary" aria-hidden="true" />영상 제목</legend>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {plan.title_candidates.map((title, index) => <label key={title} className="title-option" data-selected={selectedTitle === title}><input type="radio" name="video-title" value={title} checked={selectedTitle === title} onChange={() => setSelectedTitle(title)} disabled={busy} /><span className="title-index">{index + 1}</span><span className="min-w-0 flex-1">{title}</span></label>)}
        </div>
        <label className="mt-3 block text-xs font-semibold text-muted" htmlFor="selected-title">확정 제목 직접 수정</label>
        <input id="selected-title" className="text-input mt-2" value={selectedTitle} maxLength={120} disabled={busy} onChange={(event) => setSelectedTitle(event.target.value)} />
      </fieldset>

      <div className="mt-8">
        <div className="flex items-center gap-2"><FileText size={17} className="text-primary" aria-hidden="true" /><h3 className="font-semibold">편집 가능한 섹션 타임라인</h3></div>
        <p className="mt-2 text-xs leading-5 text-muted">도입과 결론은 고정됩니다. 중간 섹션만 위아래로 이동할 수 있습니다.</p>
        <ol className="editorial-timeline mt-4">
          {sections.map((section, index) => <EditableSection key={section.section_id} section={section} index={index} total={sections.length} titleById={titleById} busy={busy} onMove={moveSection} onChange={updateSection} />)}
        </ol>
      </div>

      <div className="mt-3 flex flex-col gap-4 rounded-[14px] border border-hairline-soft p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3 text-sm leading-6 text-muted"><Sparkles size={18} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" /><p>확정하면 원본을 보존한 새 구성안 리비전에서 {selection.selected_books.length}권의 근거만 사용해 대본을 만듭니다.</p></div>
        <button type="button" className="primary-button shrink-0" disabled={busy || !valid} onClick={() => void onGenerateScript({selected_title: selectedTitle.trim(), sections: sections.map((section) => ({section_id: section.section_id, title: section.title.trim(), purpose: section.purpose.trim()}))})}>{busy ? "대본 생성 중" : "구성안 확정 · 대본 만들기"}</button>
      </div>
    </section>
  );
}

function EditableSection({section, index, total, titleById, busy, onMove, onChange}: {section: NarrativeSection; index: number; total: number; titleById: Map<string, string>; busy: boolean; onMove: (index: number, direction: -1 | 1) => void; onChange: (id: string, field: "title" | "purpose", value: string) => void}) {
  const duration = section.estimated_seconds;
  return (
    <li className="editorial-section">
      <div className="section-rail"><span className="timeline-marker">{index + 1}</span><GripVertical size={16} className="text-muted-soft" aria-hidden="true" /></div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center justify-between gap-2"><div className="flex items-center gap-2"><span className="function-badge">{FUNCTION_LABELS[section.narrative_function] ?? section.narrative_function}</span><span className="text-xs text-muted">배정 {Math.floor(duration / 60)}분 {duration % 60}초</span></div><div className="flex gap-1"><button type="button" className="order-button" disabled={busy || index <= 1} onClick={() => onMove(index, -1)} aria-label={`${section.title} 섹션을 위로`}><ArrowUp size={15} /></button><button type="button" className="order-button" disabled={busy || index >= total - 2} onClick={() => onMove(index, 1)} aria-label={`${section.title} 섹션을 아래로`}><ArrowDown size={15} /></button></div></div>
        <label className="mt-3 block text-xs font-semibold text-muted" htmlFor={`section-title-${section.section_id}`}>섹션 제목</label><input id={`section-title-${section.section_id}`} className="text-input mt-1" maxLength={120} value={section.title} disabled={busy} onChange={(event) => onChange(section.section_id, "title", event.target.value)} />
        <label className="mt-3 block text-xs font-semibold text-muted" htmlFor={`section-purpose-${section.section_id}`}>이 섹션의 목적</label><textarea id={`section-purpose-${section.section_id}`} className="section-purpose mt-1" maxLength={500} value={section.purpose} disabled={busy} onChange={(event) => onChange(section.section_id, "purpose", event.target.value)} />
        {section.book_ids.length ? <p className="mt-3 text-xs text-muted-soft">잠긴 근거 도서 · {section.book_ids.map((id) => titleById.get(id) ?? id).join(" · ")}</p> : <p className="mt-3 text-xs text-muted-soft">내레이션 연결 섹션 · 도서 근거 없음</p>}
      </div>
    </li>
  );
}
