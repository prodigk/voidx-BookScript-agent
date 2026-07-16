import {Check, Layers3, LoaderCircle, Sparkles} from "lucide-react";

import type {OutlineJob} from "@/types/api";

const STEPS = [
  {key: "queued", label: "선택 검증", icon: Check},
  {key: "selection_revision", label: "새 실행 보존", icon: Layers3},
  {key: "phase5_narrative", label: "구성안 설계", icon: Sparkles},
  {key: "outline_ready", label: "검토 준비", icon: Check},
];

export function OutlineProgress({job}: {job: OutlineJob}) {
  const failed = job.status === "failed";
  const current = Math.max(0, STEPS.findIndex((step) => step.key === job.stage));
  return (
    <section className="workspace-card mt-6 overflow-hidden" aria-live="polite" aria-label="구성안 생성 상태">
      <div className="flex items-center justify-between gap-4 border-b border-hairline-soft px-5 py-5 sm:px-7">
        <div><p className="eyebrow">Phase 5</p><h2 className="mt-2 text-lg font-semibold">{failed ? "구성안을 완료하지 못했습니다" : job.status === "succeeded" ? "영상 구성안이 준비됐습니다" : "선택한 책을 이야기로 엮고 있습니다"}</h2></div>
        {job.status === "queued" || job.status === "running" ? <LoaderCircle className="animate-spin text-primary motion-reduce:animate-none" size={22} aria-hidden="true" /> : null}
      </div>
      <ol className="outline-ribbon">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          return <li key={step.key} className="ribbon-step" data-active={!failed && index === current} data-complete={!failed && index < current}><span className="ribbon-icon"><Icon size={16} aria-hidden="true" /></span><span>{step.label}</span></li>;
        })}
      </ol>
      {job.error ? <p role="alert" className="border-t border-hairline-soft bg-[#fff8f6] px-5 py-4 text-sm text-error sm:px-7">{job.error}</p> : null}
    </section>
  );
}
