"use client";

import {useMemo, useState} from "react";
import {AlertTriangle, CheckCircle2, Download, FilePenLine, FileWarning, ShieldCheck} from "lucide-react";

import {artifactDownloadUrl} from "@/lib/api";
import type {CitationRecord, ValidationArtifacts, ValidationIssue} from "@/types/api";

const CATEGORY_LABELS: Record<string, string> = {
  missing_source: "출처 누락", invalid_line_range: "행 범위 오류", modified_quotation: "인용문 변경",
  unsupported_paraphrase: "지원되지 않는 요약", mixed_book_attribution: "도서 귀속 혼합",
  incorrect_title: "도서 제목 오류", incorrect_author: "저자 오류", unsupported_causal_claim: "근거 없는 인과관계",
};
const TARGETED_REWRITE_CATEGORIES = new Set(["unsupported_paraphrase", "unsupported_causal_claim"]);

type IssueGroup = {
  paragraphId: string;
  sectionId: string;
  issues: ValidationIssue[];
  citation?: CitationRecord;
  eligible: boolean;
};

export function ValidationResult({
  artifacts,
  busy = false,
  onRevise,
}: {
  artifacts: ValidationArtifacts;
  busy?: boolean;
  onRevise?: (paragraphIds: string[]) => void | Promise<void>;
}) {
  const {result} = artifacts;
  const approved = result.status === "approved";
  const attention = result.citations.filter((citation) => citation.status !== "valid");
  const groups = useMemo(() => groupIssues(result.issues, result.citations), [result]);
  const eligibleIds = useMemo(
    () => groups.filter((group) => group.eligible).map((group) => group.paragraphId),
    [groups],
  );
  const [selection, setSelection] = useState<{runId: string; ids: string[]} | null>(null);
  const selected = selection?.runId === artifacts.runId ? selection.ids : eligibleIds;

  const toggle = (paragraphId: string) => {
    setSelection({
      runId: artifacts.runId,
      ids: selected.includes(paragraphId)
        ? selected.filter((item) => item !== paragraphId)
        : [...selected, paragraphId],
    });
  };

  return (
    <section className="workspace-card mt-6 p-5 sm:p-7 lg:p-8" aria-labelledby="validation-title">
      <div className="validation-hero" data-approved={approved}>
        <div className="validation-emblem">{approved ? <CheckCircle2 size={25} aria-hidden="true" /> : <AlertTriangle size={25} aria-hidden="true" />}</div>
        <div><p className="eyebrow">Citation ledger</p><h2 id="validation-title" className="mt-2 text-[22px] font-semibold">{approved ? "출처 검증 승인" : "수정이 필요한 대본"}</h2><p className="mt-2 text-sm leading-6 text-muted">{approved ? "고위험 출처 문제가 발견되지 않았습니다." : "고위험 이슈가 있는 문단만 선택해 새 리비전으로 재작성하고 자동으로 다시 검증할 수 있습니다."}</p></div>
      </div>
      <dl className="validation-stats mt-5">
        <Stat label="유효" value={result.valid_count} tone="valid" />
        <Stat label="사람 검토" value={result.needs_review_count} tone="review" />
        <Stat label="무효" value={result.invalid_count} tone="invalid" />
      </dl>

      <div className="mt-7">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2"><FileWarning size={17} className="text-primary" aria-hidden="true" /><h3 className="font-semibold">검증 이슈 {result.issues.length}건</h3></div>
          {eligibleIds.length > 1 ? <button type="button" className="text-sm font-semibold text-ink underline decoration-hairline underline-offset-4" onClick={() => setSelection({runId: artifacts.runId, ids: selected.length === eligibleIds.length ? [] : eligibleIds})}>{selected.length === eligibleIds.length ? "전체 선택 해제" : "재작성 문단 전체 선택"}</button> : null}
        </div>
        {groups.length === 0 ? <div className="mt-3 rounded-[14px] bg-surface-soft p-4 text-sm text-muted">발견된 고위험 문제가 없습니다.</div> : (
          <ol className="mt-3 grid gap-3">
            {groups.map((group) => (
              <li key={group.paragraphId} className="issue-card" data-severity={highestSeverity(group.issues)} data-selected={selected.includes(group.paragraphId)}>
                <div className="flex items-start gap-3">
                  {group.eligible ? <input id={`revision-${group.paragraphId}`} className="revision-checkbox" type="checkbox" checked={selected.includes(group.paragraphId)} disabled={busy} onChange={() => toggle(group.paragraphId)} aria-label={`${group.paragraphId} 문단 재작성 선택`} /> : null}
                  <div className="min-w-0 flex-1">
                    <label htmlFor={group.eligible ? `revision-${group.paragraphId}` : undefined} className={group.eligible ? "cursor-pointer" : undefined}>
                      <span className="flex flex-wrap items-center gap-2"><span className="severity-badge">{severityLabel(highestSeverity(group.issues))}</span><span className="text-xs font-semibold text-muted">{group.issues.map((issue) => CATEGORY_LABELS[issue.category] ?? issue.category).join(" · ")}</span><span className="text-xs text-muted-soft">{group.sectionId} · {group.paragraphId}</span></span>
                      {group.citation ? <span className="mt-3 block rounded-[10px] bg-white p-3 text-sm leading-6 text-ink">{group.citation.text}</span> : null}
                    </label>
                    {group.issues.map((issue) => <div key={issue.issue_id} className="mt-3 text-sm leading-6"><p className="text-ink">{issue.description}</p><p className="mt-1 text-muted"><strong className="text-ink">재작성 제안:</strong> {issue.recommended_action}</p></div>)}
                    {!group.eligible ? <p className="mt-3 text-xs leading-5 text-error">자동 재작성보다 원본·인덱스 확인이 먼저 필요한 이슈입니다.</p> : null}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
        {!approved && eligibleIds.length > 0 && onRevise ? (
          <div className="revision-action mt-4">
            <div><p className="text-sm font-semibold text-ink">선택한 {selected.length}개 문단만 새 실행에 반영합니다</p><p className="mt-1 text-xs leading-5 text-muted">원본 실행은 보존되며 재작성 직후 출처 검증이 자동으로 다시 실행됩니다.</p></div>
            <button type="button" className="primary-button" disabled={busy || selected.length === 0} onClick={() => void onRevise(selected)}><FilePenLine size={17} aria-hidden="true" />{busy ? "재작성 중" : "재작성 후 다시 검증"}</button>
          </div>
        ) : null}
      </div>

      <div className="mt-7">
        <div className="flex items-center gap-2"><ShieldCheck size={17} className="text-primary" aria-hidden="true" /><h3 className="font-semibold">문단별 출처 확인</h3></div>
        <div className="mt-3 grid gap-2">{(attention.length ? attention : result.citations).map((citation) => <CitationDetail key={citation.citation_id} citation={citation} />)}</div>
      </div>

      <div className="mt-6 flex flex-wrap justify-end gap-2"><a className="secondary-button compact" href={artifactDownloadUrl(artifacts.runId, "validation_report.md")}><Download size={15} aria-hidden="true" />검증 리포트</a><a className="secondary-button compact" href={artifactDownloadUrl(artifacts.runId, "citations.json")}><Download size={15} aria-hidden="true" />검증 JSON</a></div>
    </section>
  );
}

function groupIssues(issues: ValidationIssue[], citations: CitationRecord[]): IssueGroup[] {
  const citationByParagraph = new Map(citations.map((citation) => [citation.paragraph_id, citation]));
  const grouped = new Map<string, ValidationIssue[]>();
  for (const issue of issues) grouped.set(issue.paragraph_id, [...(grouped.get(issue.paragraph_id) ?? []), issue]);
  return [...grouped.entries()].map(([paragraphId, paragraphIssues]) => ({
    paragraphId,
    sectionId: paragraphIssues[0].section_id,
    issues: paragraphIssues,
    citation: citationByParagraph.get(paragraphId),
    eligible: paragraphIssues.some((issue) => issue.severity === "high" && TARGETED_REWRITE_CATEGORIES.has(issue.category)) && citationByParagraph.has(paragraphId),
  }));
}

function highestSeverity(issues: ValidationIssue[]): ValidationIssue["severity"] {
  return issues.some((issue) => issue.severity === "high") ? "high" : issues.some((issue) => issue.severity === "medium") ? "medium" : "low";
}

function severityLabel(severity: ValidationIssue["severity"]): string { return severity === "high" ? "높음" : severity === "medium" ? "중간" : "낮음"; }

function Stat({label, value, tone}: {label: string; value: number; tone: string}) { return <div className="validation-stat" data-tone={tone}><dt>{label}</dt><dd>{value}</dd></div>; }

function CitationDetail({citation}: {citation: CitationRecord}) {
  const status = citation.status === "valid" ? "유효" : citation.status === "needs_review" ? "사람 검토" : "무효";
  return <details className="citation-detail"><summary><span className="citation-status" data-status={citation.status}>{status}</span><span className="min-w-0 flex-1 truncate">{citation.section_id} · {citation.paragraph_id}</span><span>{Math.round(citation.confidence * 100)}%</span></summary><div className="citation-body"><p className="text-sm leading-6 text-ink">{citation.text}</p><p className="mt-3 text-xs leading-5 text-muted">{citation.review_summary}</p>{citation.sources.length ? <ul className="mt-3 grid gap-1">{citation.sources.map((source) => <li key={source.chunk_id} className="source-line">{source.title} · {source.source_file}:{source.start_line}-{source.end_line}{source.heading_path.length ? ` · ${source.heading_path.join(" › ")}` : ""}</li>)}</ul> : <p className="mt-3 text-xs text-error">연결된 원본 위치가 없습니다.</p>}</div></details>;
}
