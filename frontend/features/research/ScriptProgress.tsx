import {Check, FilePenLine, LoaderCircle, ScrollText, Sparkles} from "lucide-react";

import type {ScriptJob} from "@/types/api";

const STEPS = [
  {key: "queued", label: "편집 검증", icon: Check},
  {key: "narrative_revision", label: "리비전 보존", icon: FilePenLine},
  {key: "phase6_script", label: "대본 작성", icon: Sparkles},
  {key: "script_ready", label: "검토 준비", icon: ScrollText},
];

export function ScriptProgress({job}: {job: ScriptJob}) {
  const failed = job.status === "failed";
  const current = Math.max(0, STEPS.findIndex((step) => step.key === job.stage));
  return (
    <section className="workspace-card mt-6 overflow-hidden" aria-live="polite" aria-label="대본 생성 상태">
      <div className="flex items-center justify-between gap-4 border-b border-hairline-soft px-5 py-5 sm:px-7">
        <div><p className="eyebrow">Phase 6</p><h2 className="mt-2 text-lg font-semibold">{failed ? "대본을 완료하지 못했습니다" : job.status === "succeeded" ? "검토할 대본이 준비됐습니다" : "근거를 내레이션으로 바꾸고 있습니다"}</h2></div>
        {job.status === "queued" || job.status === "running" ? <LoaderCircle className="animate-spin text-primary motion-reduce:animate-none" size={22} aria-hidden="true" /> : null}
      </div>
      <ol className="outline-ribbon">
        {STEPS.map((step, index) => { const Icon = step.icon; return <li key={step.key} className="ribbon-step" data-active={!failed && index === current} data-complete={!failed && index < current}><span className="ribbon-icon"><Icon size={16} aria-hidden="true" /></span><span>{step.label}</span></li>; })}
      </ol>
      {job.error ? <p role="alert" className="border-t border-hairline-soft bg-[#fff8f6] px-5 py-4 text-sm text-error sm:px-7">{job.error}</p> : null}
    </section>
  );
}
