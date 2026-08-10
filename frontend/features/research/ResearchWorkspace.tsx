"use client";

import {useEffect, useRef, useState} from "react";
import {BookMarked, Database, RotateCcw, WifiOff} from "lucide-react";

import {createCitationRevisionJob, createOutlineJob, createResearchJob, createScriptJob, createValidationJob, getLibraryStatus, getNarrativeArtifact, getResearchArtifacts, getResearchJob, getScriptArtifacts, getValidationArtifacts} from "@/lib/api";
import type {CandidateBook, CitationRevisionJob, LibraryStatus, NarrativePlan, OutlineJob, ResearchJob, ResearchRequest, ScriptArtifacts, ScriptJob, ScriptJobRequest, SelectionArtifact, ValidationArtifacts, ValidationJob} from "@/types/api";
import {JobProgress} from "./JobProgress";
import {OutlineProgress} from "./OutlineProgress";
import {OutlineResult} from "./OutlineResult";
import {ResearchResult} from "./ResearchResult";
import {ScriptProgress} from "./ScriptProgress";
import {ScriptResult} from "./ScriptResult";
import {TopicForm} from "./TopicForm";
import {CitationRevisionProgress, ValidationProgress} from "./ValidationProgress";
import {ValidationResult} from "./ValidationResult";

const POLL_INTERVAL_MS = 1500;

export function ResearchWorkspace() {
  const [library, setLibrary] = useState<LibraryStatus | null>(null);
  const [libraryError, setLibraryError] = useState(false);
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [outlineJob, setOutlineJob] = useState<OutlineJob | null>(null);
  const [result, setResult] = useState<{candidates: CandidateBook[]; selection: SelectionArtifact} | null>(null);
  const [outline, setOutline] = useState<{plan: NarrativePlan; selection: SelectionArtifact} | null>(null);
  const [scriptJob, setScriptJob] = useState<ScriptJob | null>(null);
  const [script, setScript] = useState<ScriptArtifacts | null>(null);
  const [validationJob, setValidationJob] = useState<ValidationJob | null>(null);
  const [validation, setValidation] = useState<ValidationArtifacts | null>(null);
  const [citationRevisionJob, setCitationRevisionJob] = useState<CitationRevisionJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    getLibraryStatus().then((status) => alive.current && setLibrary(status)).catch(() => alive.current && setLibraryError(true));
    return () => { alive.current = false; };
  }, []);

  const poll = async (jobId: string) => {
    while (alive.current) {
      await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
      if (!alive.current) return;
      const latest = await getResearchJob(jobId);
      if (latest.kind !== "research") throw new Error("연구 작업이 아닌 상태 응답을 받았습니다.");
      setJob(latest);
      if (latest.status === "failed") return;
      if (latest.status === "succeeded") {
        if (latest.pipeline_status === "insufficient_evidence" || !latest.run_id) return;
        const artifacts = await getResearchArtifacts(latest.run_id);
        if (alive.current) setResult(artifacts);
        return;
      }
    }
  };

  const pollOutline = async (jobId: string) => {
    while (alive.current) {
      await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
      if (!alive.current) return;
      const latest = await getResearchJob(jobId);
      if (latest.kind !== "outline") throw new Error("구성안 작업이 아닌 상태 응답을 받았습니다.");
      setOutlineJob(latest);
      if (latest.status === "failed") return;
      if (latest.status === "succeeded") {
        if (!latest.run_id) throw new Error("구성안 실행 ID를 찾을 수 없습니다.");
        const [plan, artifacts] = await Promise.all([
          getNarrativeArtifact(latest.run_id),
          getResearchArtifacts(latest.run_id),
        ]);
        if (alive.current) setOutline({plan, selection: artifacts.selection});
        return;
      }
    }
  };

  const pollScript = async (jobId: string) => {
    while (alive.current) {
      await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
      if (!alive.current) return;
      const latest = await getResearchJob(jobId);
      if (latest.kind !== "script") throw new Error("대본 작업이 아닌 상태 응답을 받았습니다.");
      setScriptJob(latest);
      if (latest.status === "failed") return;
      if (latest.status === "succeeded") {
        if (!latest.run_id) throw new Error("대본 실행 ID를 찾을 수 없습니다.");
        const artifacts = await getScriptArtifacts(latest.run_id);
        if (alive.current) setScript(artifacts);
        return;
      }
    }
  };

  const pollValidation = async (jobId: string) => {
    while (alive.current) {
      await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
      if (!alive.current) return;
      const latest = await getResearchJob(jobId);
      if (latest.kind !== "validation") throw new Error("검증 작업이 아닌 상태 응답을 받았습니다.");
      setValidationJob(latest);
      if (latest.status === "failed") return;
      if (latest.status === "succeeded") {
        if (!latest.run_id) throw new Error("검증 실행 ID를 찾을 수 없습니다.");
        const artifacts = await getValidationArtifacts(latest.run_id);
        if (alive.current) setValidation(artifacts);
        return;
      }
    }
  };

  const pollCitationRevision = async (jobId: string) => {
    while (alive.current) {
      await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
      if (!alive.current) return;
      const latest = await getResearchJob(jobId);
      if (latest.kind !== "citation_revision") throw new Error("부분 재작성 작업이 아닌 상태 응답을 받았습니다.");
      setCitationRevisionJob(latest);
      if (latest.status === "failed") return;
      if (latest.status === "succeeded") {
        if (!latest.run_id) throw new Error("부분 재작성 실행 ID를 찾을 수 없습니다.");
        const [scriptArtifacts, validationArtifacts] = await Promise.all([
          getScriptArtifacts(latest.run_id),
          getValidationArtifacts(latest.run_id),
        ]);
        if (alive.current) {
          setScript(scriptArtifacts);
          setValidation(validationArtifacts);
        }
        return;
      }
    }
  };

  const startResearch = async (request: ResearchRequest) => {
    setError(null);
    setResult(null);
    setOutline(null);
    setOutlineJob(null);
    setScriptJob(null);
    setScript(null);
    setValidationJob(null);
    setValidation(null);
    setCitationRevisionJob(null);
    try {
      const created = await createResearchJob(request);
      setJob(created);
      void poll(created.job_id).catch((reason: unknown) => {
        if (alive.current) setError(reason instanceof Error ? reason.message : "작업 상태를 확인할 수 없습니다.");
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "연구 작업을 시작할 수 없습니다.");
    }
  };

  const generateOutline = async (selectedBookIds: string[]) => {
    if (!job?.run_id) return;
    setError(null);
    setOutline(null);
    setScript(null);
    setScriptJob(null);
    setValidationJob(null);
    setValidation(null);
    setCitationRevisionJob(null);
    try {
      const created = await createOutlineJob(job.run_id, selectedBookIds);
      setOutlineJob(created);
      void pollOutline(created.job_id).catch((reason: unknown) => {
        if (alive.current) setError(reason instanceof Error ? reason.message : "구성안 상태를 확인할 수 없습니다.");
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "구성안 작업을 시작할 수 없습니다.");
    }
  };

  const generateScript = async (payload: Omit<ScriptJobRequest, "source_run_id">) => {
    if (!outlineJob?.run_id) return;
    setError(null);
    setScript(null);
    setValidationJob(null);
    setValidation(null);
    setCitationRevisionJob(null);
    try {
      const created = await createScriptJob(outlineJob.run_id, payload);
      setScriptJob(created);
      void pollScript(created.job_id).catch((reason: unknown) => {
        if (alive.current) setError(reason instanceof Error ? reason.message : "대본 상태를 확인할 수 없습니다.");
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "대본 작업을 시작할 수 없습니다.");
    }
  };

  const validateScript = async () => {
    if (!script?.runId) return;
    setError(null);
    setValidation(null);
    setCitationRevisionJob(null);
    try {
      const created = await createValidationJob(script.runId);
      setValidationJob(created);
      void pollValidation(created.job_id).catch((reason: unknown) => {
        if (alive.current) setError(reason instanceof Error ? reason.message : "검증 상태를 확인할 수 없습니다.");
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "출처 검증 작업을 시작할 수 없습니다.");
    }
  };

  const reviseAndRevalidate = async (paragraphIds: string[]) => {
    if (!validation?.runId) return;
    setError(null);
    setValidationJob(null);
    try {
      const created = await createCitationRevisionJob(validation.runId, paragraphIds);
      setCitationRevisionJob(created);
      void pollCitationRevision(created.job_id).catch((reason: unknown) => {
        if (alive.current) setError(reason instanceof Error ? reason.message : "부분 재작성 상태를 확인할 수 없습니다.");
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "부분 재작성 작업을 시작할 수 없습니다.");
    }
  };

  const busy = job?.status === "queued" || job?.status === "running" || outlineJob?.status === "queued" || outlineJob?.status === "running" || scriptJob?.status === "queued" || scriptJob?.status === "running" || validationJob?.status === "queued" || validationJob?.status === "running" || citationRevisionJob?.status === "queued" || citationRevisionJob?.status === "running";

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <header className="top-nav">
        <div className="page-container flex h-full items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="brand-mark" aria-hidden="true"><BookMarked size={20} /></span>
            <div><p className="font-semibold tracking-[-0.02em]">Bookscript</p><p className="text-[11px] text-muted">Evidence studio</p></div>
          </div>
          <div className="library-pill" data-error={libraryError}>
            {libraryError ? <WifiOff size={14} aria-hidden="true" /> : <Database size={14} aria-hidden="true" />}
            <span>{libraryError ? "로컬 API 연결 필요" : library ? `도서 ${library.book_count}권 · 청크 ${library.chunk_count.toLocaleString("ko-KR")}개` : "서재 확인 중"}</span>
          </div>
        </div>
      </header>

      <div className="page-container py-10 sm:py-14 lg:py-16">
        <section className="hero-grid">
          <div>
            <p className="eyebrow">Local-first · Evidence-first</p>
            <h1 className="mt-4 max-w-3xl text-[32px] font-semibold leading-[1.22] tracking-[-0.035em] sm:text-[42px]">한 가지 질문에서,<br /><span className="text-primary">검증 가능한 이야기</span>까지.</h1>
          </div>
          <p className="max-w-md self-end text-sm leading-6 text-muted sm:text-base sm:leading-7">로컬에 보관된 도서 노트를 검색하고, 책마다 다른 관점을 엮어 한국어 영상 리서치를 설계합니다.</p>
        </section>

        <div className="mt-10 grid items-start gap-6 lg:grid-cols-[minmax(0,1.12fr)_minmax(340px,0.88fr)]">
          <TopicForm disabled={busy} onSubmit={startResearch} />
          <aside className="grid gap-6 lg:sticky lg:top-6">
            {job ? <JobProgress job={job} /> : <EmptyProcess />}
            {error ? (
              <div className="error-card" role="alert">
                <p className="font-semibold text-ink">연결을 다시 확인해 주세요</p>
                <p className="mt-1 text-sm leading-6 text-muted">{error}</p>
                <button type="button" onClick={() => setError(null)} className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-ink"><RotateCcw size={15} />닫기</button>
              </div>
            ) : null}
          </aside>
        </div>

        {job?.pipeline_status === "insufficient_evidence" ? (
          <section className="mt-6 rounded-[20px] border border-[#f1d7c8] bg-[#fff8f3] p-6" role="status">
            <h2 className="font-semibold">충분한 근거를 찾지 못했습니다</h2>
            <p className="mt-2 text-sm leading-6 text-muted">주제를 조금 더 구체화하거나 관점을 넓혀 다시 검색해 주세요. 근거 없이 대본을 생성하지 않았습니다.</p>
          </section>
        ) : null}
        {result ? <div className="mt-6"><ResearchResult candidates={result.candidates} selection={result.selection} contentFormat={job?.request.content_format} busy={Boolean((outlineJob && outlineJob.status !== "failed" && outlineJob.status !== "succeeded") || (scriptJob && scriptJob.status !== "failed" && scriptJob.status !== "succeeded") || (validationJob && validationJob.status !== "failed" && validationJob.status !== "succeeded"))} onGenerateOutline={generateOutline} /></div> : null}
        {outlineJob ? <OutlineProgress job={outlineJob} /> : null}
        {outline && result ? <OutlineResult plan={outline.plan} selection={outline.selection} candidates={result.candidates} busy={Boolean((scriptJob && scriptJob.status !== "failed" && scriptJob.status !== "succeeded") || (validationJob && validationJob.status !== "failed" && validationJob.status !== "succeeded"))} onGenerateScript={generateScript} /> : null}
        {scriptJob ? <ScriptProgress job={scriptJob} /> : null}
        {script ? <ScriptResult artifacts={script} busy={Boolean(validationJob && validationJob.status !== "failed" && validationJob.status !== "succeeded")} validated={Boolean(validation)} onValidate={validateScript} /> : null}
        {validationJob ? <ValidationProgress job={validationJob} /> : null}
        {citationRevisionJob ? <CitationRevisionProgress job={citationRevisionJob} /> : null}
        {validation ? <ValidationResult artifacts={validation} busy={Boolean(citationRevisionJob && citationRevisionJob.status !== "failed" && citationRevisionJob.status !== "succeeded")} onRevise={reviseAndRevalidate} /> : null}
      </div>
    </main>
  );
}

function EmptyProcess() {
  return (
    <section className="workspace-card p-6 sm:p-7">
      <p className="eyebrow">Research ribbon</p>
      <h2 className="mt-2 text-lg font-semibold">리서치가 시작되면</h2>
      <ol className="mt-5 grid gap-4 text-sm text-muted">
        {["주제를 여러 검색 질문으로 나눕니다", "관련 도서와 원문 근거를 비교합니다", "최종 후보와 선정 이유를 정리합니다"].map((item, index) => (
          <li key={item} className="flex items-start gap-3"><span className="empty-step">{index + 1}</span><span className="pt-1 leading-5">{item}</span></li>
        ))}
      </ol>
      <p className="mt-6 border-t border-hairline-soft pt-5 text-xs leading-5 text-muted-soft">전체 서재는 외부 API로 전송하지 않습니다. 검색으로 선정된 청크만 사용합니다.</p>
    </section>
  );
}
