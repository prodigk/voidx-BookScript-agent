import {AlertTriangle, CheckCircle2, Download, FileWarning, ShieldCheck} from "lucide-react";

import {artifactDownloadUrl} from "@/lib/api";
import type {CitationRecord, ValidationArtifacts} from "@/types/api";

const CATEGORY_LABELS: Record<string, string> = {
  missing_source: "출처 누락", invalid_line_range: "행 범위 오류", modified_quotation: "인용문 변경",
  unsupported_paraphrase: "지원되지 않는 요약", mixed_book_attribution: "도서 귀속 혼합",
  incorrect_title: "도서 제목 오류", incorrect_author: "저자 오류", unsupported_causal_claim: "근거 없는 인과관계",
};

export function ValidationResult({artifacts}: {artifacts: ValidationArtifacts}) {
  const {result} = artifacts;
  const approved = result.status === "approved";
  const attention = result.citations.filter((citation) => citation.status !== "valid");
  return (
    <section className="workspace-card mt-6 p-5 sm:p-7 lg:p-8" aria-labelledby="validation-title">
      <div className="validation-hero" data-approved={approved}>
        <div className="validation-emblem">{approved ? <CheckCircle2 size={25} aria-hidden="true" /> : <AlertTriangle size={25} aria-hidden="true" />}</div>
        <div><p className="eyebrow">Citation ledger</p><h2 id="validation-title" className="mt-2 text-[22px] font-semibold">{approved ? "출처 검증 승인" : "수정이 필요한 대본"}</h2><p className="mt-2 text-sm leading-6 text-muted">{approved ? "고위험 출처 문제가 발견되지 않았습니다." : "아래 이슈를 확인한 뒤 해당 문단만 수정하는 것이 안전합니다."}</p></div>
      </div>
      <dl className="validation-stats mt-5">
        <Stat label="유효" value={result.valid_count} tone="valid" />
        <Stat label="사람 검토" value={result.needs_review_count} tone="review" />
        <Stat label="무효" value={result.invalid_count} tone="invalid" />
      </dl>

      <div className="mt-7">
        <div className="flex items-center gap-2"><FileWarning size={17} className="text-primary" aria-hidden="true" /><h3 className="font-semibold">검증 이슈 {result.issues.length}건</h3></div>
        {result.issues.length === 0 ? <div className="mt-3 rounded-[14px] bg-surface-soft p-4 text-sm text-muted">발견된 고위험 문제가 없습니다.</div> : <ol className="mt-3 grid gap-3">{result.issues.map((issue) => <li key={issue.issue_id} className="issue-card" data-severity={issue.severity}><div className="flex flex-wrap items-center gap-2"><span className="severity-badge">{issue.severity === "high" ? "높음" : issue.severity === "medium" ? "중간" : "낮음"}</span><span className="text-xs font-semibold text-muted">{CATEGORY_LABELS[issue.category] ?? issue.category}</span><span className="text-xs text-muted-soft">{issue.section_id} · {issue.paragraph_id}</span></div><p className="mt-3 text-sm leading-6 text-ink">{issue.description}</p><p className="mt-2 text-sm leading-6 text-muted"><strong className="text-ink">권장 조치:</strong> {issue.recommended_action}</p></li>)}</ol>}
      </div>

      <div className="mt-7">
        <div className="flex items-center gap-2"><ShieldCheck size={17} className="text-primary" aria-hidden="true" /><h3 className="font-semibold">문단별 출처 확인</h3></div>
        <div className="mt-3 grid gap-2">{(attention.length ? attention : result.citations).map((citation) => <CitationDetail key={citation.citation_id} citation={citation} />)}</div>
      </div>

      <div className="mt-6 flex flex-wrap justify-end gap-2"><a className="secondary-button compact" href={artifactDownloadUrl(artifacts.runId, "validation_report.md")}><Download size={15} aria-hidden="true" />검증 리포트</a><a className="secondary-button compact" href={artifactDownloadUrl(artifacts.runId, "citations.json")}><Download size={15} aria-hidden="true" />검증 JSON</a></div>
    </section>
  );
}

function Stat({label, value, tone}: {label: string; value: number; tone: string}) { return <div className="validation-stat" data-tone={tone}><dt>{label}</dt><dd>{value}</dd></div>; }

function CitationDetail({citation}: {citation: CitationRecord}) {
  const status = citation.status === "valid" ? "유효" : citation.status === "needs_review" ? "사람 검토" : "무효";
  return <details className="citation-detail"><summary><span className="citation-status" data-status={citation.status}>{status}</span><span className="min-w-0 flex-1 truncate">{citation.section_id} · {citation.paragraph_id}</span><span>{Math.round(citation.confidence * 100)}%</span></summary><div className="citation-body"><p className="text-sm leading-6 text-ink">{citation.text}</p><p className="mt-3 text-xs leading-5 text-muted">{citation.review_summary}</p>{citation.sources.length ? <ul className="mt-3 grid gap-1">{citation.sources.map((source) => <li key={source.chunk_id} className="source-line">{source.title} · {source.source_file}:{source.start_line}-{source.end_line}{source.heading_path.length ? ` · ${source.heading_path.join(" › ")}` : ""}</li>)}</ul> : <p className="mt-3 text-xs text-error">연결된 원본 위치가 없습니다.</p>}</div></details>;
}
