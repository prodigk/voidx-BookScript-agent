"use client";

import {useMemo, useState} from "react";
import {ArrowDown, ArrowUp, BookOpen, Check, ChevronDown, ChevronUp, Sparkles} from "lucide-react";

import type {CandidateBook, SelectionArtifact} from "@/types/api";

type ResearchResultProps = {
  candidates: CandidateBook[];
  selection: SelectionArtifact;
  busy?: boolean;
  onGenerateOutline: (selectedBookIds: string[]) => Promise<void>;
};

function cleanAuthor(author: string) {
  if (!author || author === "unknown") return "저자 정보 확인 필요";
  return author.replace(/^\['|']$/g, "").replace(/', '/g, ", ");
}

export function ResearchResult({candidates, selection, busy = false, onGenerateOutline}: ResearchResultProps) {
  const initial = selection.selected_books.map((book) => book.book_id);
  const [selectedIds, setSelectedIds] = useState(initial);
  const [expanded, setExpanded] = useState<string | null>(initial[0] ?? null);
  const selectedMap = useMemo(
    () => new Map(selection.selected_books.map((book) => [book.book_id, book])),
    [selection.selected_books],
  );

  const toggle = (bookId: string) => {
    setSelectedIds((current) => current.includes(bookId) ? current.filter((id) => id !== bookId) : current.length < 4 ? [...current, bookId] : current);
  };

  const move = (bookId: string, direction: -1 | 1) => {
    setSelectedIds((current) => {
      const index = current.indexOf(bookId);
      const nextIndex = index + direction;
      if (index < 0 || nextIndex < 0 || nextIndex >= current.length) return current;
      const next = [...current];
      [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
      return next;
    });
  };

  const selectedCandidates = selectedIds.map((id) => candidates.find((book) => book.book_id === id)).filter((book): book is CandidateBook => Boolean(book));

  return (
    <section className="workspace-card p-5 sm:p-7 lg:p-8" aria-labelledby="candidate-title">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">근거 검토</p>
          <h2 id="candidate-title" className="mt-2 text-[22px] font-semibold tracking-[-0.02em] text-ink">후보 도서 {candidates.length}권</h2>
          <p className="mt-2 text-sm leading-6 text-muted">점수만 보지 않고 각 책이 영상에서 맡을 관점과 선정 이유를 확인하세요.</p>
        </div>
        <div className="selection-count" aria-live="polite"><strong>{selectedIds.length}</strong> / 4권 선택</div>
      </div>

      <div className="connection-note mt-6">
        <p className="eyebrow">책을 잇는 흐름</p>
        <p className="mt-2 text-sm leading-6 text-ink">{selection.cross_book_connection}</p>
      </div>

      <div className="narrative-stack mt-6" aria-labelledby="narrative-stack-title">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow">Narrative stack</p>
            <h3 id="narrative-stack-title" className="mt-2 font-semibold text-ink">영상에서 만날 순서</h3>
          </div>
          <p className="text-xs text-muted">화살표로 이야기의 흐름을 조정하세요</p>
        </div>
        <ol className="mt-4 grid gap-2">
          {selectedCandidates.map((book, index) => (
            <li key={book.book_id} className="stack-item">
              <span className="stack-order" aria-hidden="true">{index + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink">{book.title}</p>
                <p className="mt-0.5 truncate text-xs text-muted">{book.perspective ?? selectedMap.get(book.book_id)?.role ?? "핵심 관점"}</p>
              </div>
              <div className="flex gap-1">
                <button type="button" className="order-button" disabled={index === 0 || busy} onClick={() => move(book.book_id, -1)} aria-label={`${book.title} 순서를 위로`}><ArrowUp size={15} /></button>
                <button type="button" className="order-button" disabled={index === selectedCandidates.length - 1 || busy} onClick={() => move(book.book_id, 1)} aria-label={`${book.title} 순서를 아래로`}><ArrowDown size={15} /></button>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-6 grid gap-3">
        {candidates.map((book, index) => {
          const selected = selectedIds.includes(book.book_id);
          const selectedDetail = selectedMap.get(book.book_id);
          const isExpanded = expanded === book.book_id;
          return (
            <article key={book.book_id} className="book-card" data-selected={selected}>
              <div className="flex items-start gap-4">
                <button type="button" disabled={busy} onClick={() => toggle(book.book_id)} aria-pressed={selected} aria-label={`${book.title} ${selected ? "선택 해제" : "선택"}`} className="book-select">
                  {selected ? <Check size={16} aria-hidden="true" /> : <span>{index + 1}</span>}
                </button>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-ink">{book.title}</h3>
                        {selectedDetail ? <span className="selected-badge">추천 선택</span> : null}
                      </div>
                      <p className="mt-1 text-sm text-muted">{cleanAuthor(book.author)}</p>
                    </div>
                    <div className="score-pill"><strong>{Math.round(book.score * 100)}</strong><span>적합도</span></div>
                  </div>

                  <p className="mt-3 text-sm font-medium text-ink">{book.perspective ?? selectedDetail?.role ?? "관점 분석 중"}</p>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted">{book.inclusion_reason ?? selectedDetail?.selection_reason ?? "검색 근거를 바탕으로 후보에 포함되었습니다."}</p>

                  <button type="button" onClick={() => setExpanded(isExpanded ? null : book.book_id)} aria-expanded={isExpanded} className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-ink">
                    점수와 선정 근거 {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                  {isExpanded ? (
                    <div className="mt-4 border-t border-hairline-soft pt-4">
                      <div className="score-grid">
                        <Score label="검색" value={book.retrieval_score} />
                        <Score label="주제" value={book.topic_fit_score} />
                        <Score label="편집" value={book.editorial_fit_score} />
                        <Score label="정서" value={book.emotional_fit_score} />
                      </div>
                      {selectedDetail ? <p className="mt-4 text-sm leading-6 text-muted"><strong className="text-ink">영상 역할:</strong> {selectedDetail.role}</p> : null}
                    </div>
                  ) : null}
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <div className="mt-6 flex flex-col gap-4 rounded-[14px] bg-surface-soft p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3 text-sm leading-6 text-muted">
          <BookOpen size={18} className="mt-0.5 shrink-0 text-ink" aria-hidden="true" />
          <p>{selectedIds.length < 2 ? "구성안을 만들려면 근거가 있는 책을 2권 이상 선택하세요." : "확정하면 이 순서를 보존한 새 실행 기록에서 구성안을 만듭니다."}</p>
        </div>
        <button type="button" disabled={busy || selectedIds.length < 2} className="primary-button shrink-0" onClick={() => void onGenerateOutline(selectedIds)}>
          <Sparkles size={17} aria-hidden="true" />{busy ? "구성안 생성 중" : "선택 확정 · 구성안 만들기"}
        </button>
      </div>
    </section>
  );
}

function Score({label, value}: {label: string; value?: number}) {
  const percent = value == null ? null : Math.round(value * 100);
  return (
    <div>
      <div className="flex justify-between text-xs text-muted"><span>{label}</span><span>{percent == null ? "—" : percent}</span></div>
      <div className="score-track"><span style={{width: `${percent ?? 0}%`}} /></div>
    </div>
  );
}
