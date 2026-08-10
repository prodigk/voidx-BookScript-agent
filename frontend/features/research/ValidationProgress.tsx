import {Check, FilePenLine, FileSearch, LoaderCircle, ScanSearch} from "lucide-react";

import type {CitationRevisionJob, ValidationJob} from "@/types/api";

const STEPS = [
  {key: "queued", label: "대본 확인", icon: Check},
  {key: "phase7_validation", label: "원문 대조", icon: ScanSearch},
  {key: "validation_approved", label: "승인", icon: Check},
  {key: "validation_needs_revision", label: "이슈 정리", icon: FileSearch},
];

export function ValidationProgress({job}: {job: ValidationJob}) {
  const failed = job.status === "failed";
  const doneIndex = job.stage === "validation_needs_revision" ? 3 : 2;
  const current = job.stage === "queued" ? 0 : job.status === "succeeded" ? doneIndex : 1;
  return (
    <section className="workspace-card mt-6 overflow-hidden" aria-live="polite" aria-label="출처 검증 상태">
      <div className="flex items-center justify-between gap-4 border-b border-hairline-soft px-5 py-5 sm:px-7">
        <div><p className="eyebrow">Phase 7</p><h2 className="mt-2 text-lg font-semibold">{failed ? "출처 검증을 완료하지 못했습니다" : job.status === "succeeded" ? job.pipeline_status === "approved" ? "대본이 검증을 통과했습니다" : "검토할 이슈가 발견됐습니다" : "대본과 원문을 대조하고 있습니다"}</h2></div>
        {job.status === "queued" || job.status === "running" ? <LoaderCircle className="animate-spin text-primary motion-reduce:animate-none" size={22} aria-hidden="true" /> : null}
      </div>
      <ol className="outline-ribbon">
        {STEPS.map((step, index) => { const Icon = step.icon; const hiddenBranch = job.status === "succeeded" && ((doneIndex === 2 && index === 3) || (doneIndex === 3 && index === 2)); return <li key={step.key} className="ribbon-step" data-active={!failed && index === current} data-complete={!failed && index < current && !hiddenBranch} data-muted={hiddenBranch}><span className="ribbon-icon"><Icon size={16} aria-hidden="true" /></span><span>{step.label}</span></li>; })}
      </ol>
      {job.error ? <p role="alert" className="border-t border-hairline-soft bg-[#fff8f6] px-5 py-4 text-sm text-error sm:px-7">{job.error}</p> : null}
    </section>
  );
}

const REVISION_STEPS = [
  {key: "queued", label: "문단 확인", icon: Check},
  {key: "targeted_revision", label: "부분 재작성", icon: FilePenLine},
  {key: "phase7_revalidation", label: "다시 검증", icon: ScanSearch},
  {key: "revision_done", label: "결과 확인", icon: FileSearch},
];

export function CitationRevisionProgress({job}: {job: CitationRevisionJob}) {
  const failed = job.status === "failed";
  const current = job.stage === "queued" ? 0 : job.stage === "targeted_revision" ? 1 : job.stage === "phase7_revalidation" ? 2 : 3;
  return (
    <section className="workspace-card mt-6 overflow-hidden" aria-live="polite" aria-label="선택 문단 재작성과 재검증 상태">
      <div className="flex items-center justify-between gap-4 border-b border-hairline-soft px-5 py-5 sm:px-7">
        <div><p className="eyebrow">Targeted revision</p><h2 className="mt-2 text-lg font-semibold">{failed ? "선택 문단을 재작성하지 못했습니다" : job.status === "succeeded" ? job.pipeline_status === "approved" ? "수정 대본이 검증을 통과했습니다" : "수정 후에도 확인할 이슈가 남았습니다" : "선택한 문단만 고쳐 다시 검증하고 있습니다"}</h2></div>
        {job.status === "queued" || job.status === "running" ? <LoaderCircle className="animate-spin text-primary motion-reduce:animate-none" size={22} aria-hidden="true" /> : null}
      </div>
      <ol className="outline-ribbon">
        {REVISION_STEPS.map((step, index) => { const Icon = step.icon; return <li key={step.key} className="ribbon-step" data-active={!failed && index === current} data-complete={!failed && index < current}><span className="ribbon-icon"><Icon size={16} aria-hidden="true" /></span><span>{step.label}</span></li>; })}
      </ol>
      {job.error ? <p role="alert" className="border-t border-hairline-soft bg-[#fff8f6] px-5 py-4 text-sm text-error sm:px-7">{job.error}</p> : null}
    </section>
  );
}
