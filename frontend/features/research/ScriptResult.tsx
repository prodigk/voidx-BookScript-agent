"use client";

import {useState} from "react";
import {Download, FileCheck2, ScanSearch, ShieldCheck} from "lucide-react";

import {artifactDownloadUrl} from "@/lib/api";
import type {ScriptArtifacts} from "@/types/api";

export function ScriptResult({artifacts, busy = false, validated = false, onValidate}: {artifacts: ScriptArtifacts; busy?: boolean; validated?: boolean; onValidate: () => Promise<void>}) {
  const [showSources, setShowSources] = useState(false);
  const content = showSources ? artifacts.sourced : artifacts.clean;
  return (
    <section className="workspace-card mt-6 p-5 sm:p-7 lg:p-8" aria-labelledby="script-result-title">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="eyebrow">Narration draft</p><h2 id="script-result-title" className="mt-2 text-[22px] font-semibold tracking-[-0.02em]">생성된 대본</h2><p className="mt-2 text-sm leading-6 text-muted">최종 승인 전 단계입니다. 다음 Phase 7에서 인용과 책 관련 주장을 다시 검증합니다.</p></div>
        <label className="source-toggle"><input type="checkbox" checked={showSources} onChange={(event) => setShowSources(event.target.checked)} /><span>내부 출처 표시</span></label>
      </div>
      <div className="script-paper mt-6" data-sourced={showSources}><pre>{content}</pre></div>
      <div className="mt-5 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-start gap-2 text-xs leading-5 text-muted"><ShieldCheck size={16} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" /><p>출처 마커는 검증용이며 시청자용 대본에서는 숨겨집니다.</p></div>
        <div className="flex flex-wrap gap-2">
          <a className="secondary-button compact" href={artifactDownloadUrl(artifacts.runId, "script.md")}><Download size={15} aria-hidden="true" />대본 다운로드</a>
          <a className="secondary-button compact" href={artifactDownloadUrl(artifacts.runId, "script_with_sources.md")}><FileCheck2 size={15} aria-hidden="true" />출처 포함</a>
          <button type="button" className="primary-button min-h-[38px] px-[13px] py-2 text-[13px]" disabled={busy || validated} onClick={() => void onValidate()}><ScanSearch size={15} aria-hidden="true" />{validated ? "검증 완료" : busy ? "검증 중" : "Phase 7 출처 검증"}</button>
        </div>
      </div>
    </section>
  );
}
