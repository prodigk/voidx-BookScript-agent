export type ResearchRequest = {
  topic: string;
  content_format: "longform" | "shorts";
  duration_minutes: number;
  target_book_count: number;
  tone: string;
  audience: string;
  desired_lenses: string[];
  desired_emotional_effects: string[];
  excluded_lenses: string[];
};

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

type JobBase = {
  job_id: string;
  status: JobStatus;
  stage: string;
  run_id: string | null;
  pipeline_status: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type ResearchJob = JobBase & {
  kind: "research";
  request: ResearchRequest;
};

export type OutlineJobRequest = {
  source_run_id: string;
  selected_book_ids: string[];
};

export type OutlineJob = JobBase & {
  kind: "outline";
  request: OutlineJobRequest;
};

export type NarrativeSectionRevision = {
  section_id: string;
  title: string;
  purpose: string;
};

export type ScriptJobRequest = {
  source_run_id: string;
  selected_title: string;
  sections: NarrativeSectionRevision[];
};

export type ScriptJob = JobBase & {
  kind: "script";
  request: ScriptJobRequest;
};

export type ValidationJob = JobBase & {
  kind: "validation";
  request: {source_run_id: string};
};

export type CitationRevisionJobRequest = {
  source_run_id: string;
  paragraph_ids: string[];
};

export type CitationRevisionJob = JobBase & {
  kind: "citation_revision";
  request: CitationRevisionJobRequest;
};

export type PipelineJob = ResearchJob | OutlineJob | ScriptJob | ValidationJob | CitationRevisionJob;

export type LibraryStatus = {
  library_available: boolean;
  database_available: boolean;
  source_file_count: number;
  book_count: number;
  chunk_count: number;
  embedding_count: number;
  current_embedding_count: number;
  embedding_model: string;
  embedding_dimensions: number;
  last_indexed_at: string | null;
};

export type CandidateBook = {
  book_id: string;
  title: string;
  author: string;
  score: number;
  chunk_count: number;
  retrieval_score: number;
  topic_fit_score?: number;
  editorial_fit_score?: number;
  emotional_fit_score?: number;
  perspective?: string;
  inclusion_reason?: string;
};

export type SelectedBook = {
  book_id: string;
  role: string;
  selection_reason: string;
};

export type SelectionArtifact = {
  selected_books: SelectedBook[];
  excluded_books: {book_id: string; reason: string}[];
  cross_book_connection: string;
};

export type NarrativeSection = {
  section_id: string;
  title: string;
  narrative_function: "hook" | "problem" | "book_intro" | "book_perspective" | "transition" | "tension" | "integration" | "application" | "conclusion";
  purpose: string;
  key_points: string[];
  book_ids: string[];
  evidence_ids: string[];
  estimated_seconds: number;
};

export type NarrativePlan = {
  title_candidates: string[];
  selected_title?: string | null;
  core_message: string;
  emotional_arc: string[];
  sections: NarrativeSection[];
  total_seconds: number;
};

export type ScriptArtifacts = {
  clean: string;
  sourced: string;
  runId: string;
};

export type SourceReference = {
  chunk_id: string;
  book_id: string;
  title: string;
  author: string;
  source_file: string;
  heading_path: string[];
  start_line: number;
  end_line: number;
  content_hash: string;
};

export type ValidationIssue = {
  issue_id: string;
  severity: "low" | "medium" | "high";
  category: string;
  section_id: string;
  paragraph_id: string;
  description: string;
  recommended_action: string;
  source_chunk_ids: string[];
};

export type CitationRecord = {
  citation_id: string;
  paragraph_id: string;
  section_id: string;
  text_type: string;
  text: string;
  book_ids: string[];
  evidence_ids: string[];
  sources: SourceReference[];
  status: "valid" | "needs_review" | "invalid";
  confidence: number;
  review_summary: string;
};

export type CitationValidationResult = {
  status: "approved" | "needs_revision";
  citations: CitationRecord[];
  issues: ValidationIssue[];
  valid_count: number;
  needs_review_count: number;
  invalid_count: number;
};

export type ValidationArtifacts = {
  result: CitationValidationResult;
  report: string;
  runId: string;
};
