import type {
  CandidateBook,
  LibraryStatus,
  NarrativePlan,
  OutlineJob,
  PipelineJob,
  ResearchJob,
  ResearchRequest,
  ScriptArtifacts,
  ScriptJob,
  ScriptJobRequest,
  SelectionArtifact,
  ValidationArtifacts,
  ValidationJob,
  CitationValidationResult,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {"Content-Type": "application/json", ...init?.headers},
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {detail?: string} | null;
    throw new ApiError(body?.detail ?? "로컬 백엔드 요청에 실패했습니다.", response.status);
  }
  return response.json() as Promise<T>;
}

async function requestText(path: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {detail?: string} | null;
    throw new ApiError(body?.detail ?? "생성 산출물을 읽을 수 없습니다.", response.status);
  }
  return response.text();
}

export function getLibraryStatus(): Promise<LibraryStatus> {
  return request("/api/library/status");
}

export function createResearchJob(payload: ResearchRequest): Promise<ResearchJob> {
  return request("/api/research-jobs", {method: "POST", body: JSON.stringify(payload)});
}

export function getResearchJob(jobId: string): Promise<PipelineJob> {
  return request(`/api/jobs/${encodeURIComponent(jobId)}/status`);
}

export function createOutlineJob(sourceRunId: string, selectedBookIds: string[]): Promise<OutlineJob> {
  const payload = {source_run_id: sourceRunId, selected_book_ids: selectedBookIds};
  return request(`/api/runs/${encodeURIComponent(sourceRunId)}/outline-jobs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getNarrativeArtifact(runId: string): Promise<NarrativePlan> {
  return request(`/api/runs/${encodeURIComponent(runId)}/artifacts/narrative.json`);
}

export function createScriptJob(sourceRunId: string, payload: Omit<ScriptJobRequest, "source_run_id">): Promise<ScriptJob> {
  return request(`/api/runs/${encodeURIComponent(sourceRunId)}/script-jobs`, {
    method: "POST", body: JSON.stringify({source_run_id: sourceRunId, ...payload}),
  });
}

export async function getScriptArtifacts(runId: string): Promise<ScriptArtifacts> {
  const encoded = encodeURIComponent(runId);
  const [clean, sourced] = await Promise.all([
    requestText(`/api/runs/${encoded}/artifacts/script.md`),
    requestText(`/api/runs/${encoded}/artifacts/script_with_sources.md`),
  ]);
  return {clean, sourced, runId};
}

export function createValidationJob(sourceRunId: string): Promise<ValidationJob> {
  return request(`/api/runs/${encodeURIComponent(sourceRunId)}/validation-jobs`, {
    method: "POST", body: JSON.stringify({source_run_id: sourceRunId}),
  });
}

export async function getValidationArtifacts(runId: string): Promise<ValidationArtifacts> {
  const encoded = encodeURIComponent(runId);
  const [result, report] = await Promise.all([
    request<CitationValidationResult>(`/api/runs/${encoded}/artifacts/citations.json`),
    requestText(`/api/runs/${encoded}/artifacts/validation_report.md`),
  ]);
  return {result, report, runId};
}

export function artifactDownloadUrl(runId: string, name: "script.md" | "script_with_sources.md" | "citations.json" | "validation_report.md"): string {
  return `${API_BASE_URL}/api/runs/${encodeURIComponent(runId)}/artifacts/${name}?download=true`;
}

export async function getResearchArtifacts(runId: string): Promise<{
  candidates: CandidateBook[];
  selection: SelectionArtifact;
}> {
  const encoded = encodeURIComponent(runId);
  const [candidates, selection] = await Promise.all([
    request<CandidateBook[]>(`/api/runs/${encoded}/artifacts/candidate_books.json`),
    request<SelectionArtifact>(`/api/runs/${encoded}/artifacts/selected_books.json`),
  ]);
  return {candidates, selection};
}
