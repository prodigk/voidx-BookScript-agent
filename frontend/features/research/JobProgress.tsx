import {AlertCircle, Check, LoaderCircle, Search, Sparkles} from "lucide-react";

import type {ResearchJob} from "@/types/api";

const STEPS = [
  {key: "queued", label: "요청 준비", icon: Sparkles},
  {key: "phase4_research", label: "책과 근거 탐색", icon: Search},
  {key: "research_complete", label: "후보 정리", icon: Check},
];

export function JobProgress({job}: {job: ResearchJob}) {
  const failed = job.status === "failed";
  const done = job.status === "succeeded";
  const currentIndex = job.stage === "queued" ? 0 : done ? 2 : 1;

  return (
    <section className="workspace-card overflow-hidden" aria-live="polite" aria-label="리서치 진행 상태">
      <div className="border-b border-hairline-soft px-5 py-5 sm:px-7">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="eyebrow">Research ribbon</p>
            <h2 className="mt-2 text-lg font-semibold text-ink">{failed ? "리서치를 완료하지 못했습니다" : done ? "근거 검토가 준비됐습니다" : "로컬 서재를 읽고 있습니다"}</h2>
          </div>
          {!done && !failed ? <LoaderCircle className="animate-spin text-primary motion-reduce:animate-none" size={22} aria-hidden="true" /> : null}
        </div>
      </div>
      <ol className="research-ribbon">
        {STEPS.map((step, index) => {
          const active = !failed && index === currentIndex;
          const complete = !failed && index < currentIndex;
          const Icon = failed && index === currentIndex ? AlertCircle : step.icon;
          return (
            <li key={step.key} className="ribbon-step" data-active={active} data-complete={complete} data-failed={failed && index === currentIndex}>
              <span className="ribbon-icon"><Icon size={16} aria-hidden="true" /></span>
              <span>{step.label}</span>
            </li>
          );
        })}
      </ol>
      {job.error ? <p role="alert" className="border-t border-hairline-soft bg-[#fff8f6] px-5 py-4 text-sm text-error sm:px-7">{job.error}</p> : null}
    </section>
  );
}
