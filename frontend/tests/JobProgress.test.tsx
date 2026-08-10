import {render, screen} from "@testing-library/react";
import {describe, expect, it} from "vitest";

import {JobProgress} from "@/features/research/JobProgress";
import type {ResearchJob} from "@/types/api";

const base: ResearchJob = {
  job_id: "job-1",
  kind: "research",
  status: "running",
  stage: "phase4_research",
  request: {topic: "주제", content_format: "longform", duration_minutes: 12, target_book_count: 3, tone: "사색적", audience: "일반 성인", desired_lenses: ["인문학", "철학", "심리학"], desired_emotional_effects: [], excluded_lenses: ["커리어", "생산성", "조직관리", "성과 중심"]},
  run_id: null,
  pipeline_status: null,
  error: null,
  created_at: "2026-07-14T00:00:00Z",
  started_at: "2026-07-14T00:00:01Z",
  finished_at: null,
};

describe("JobProgress", () => {
  it("announces running and failure states", () => {
    const {rerender} = render(<JobProgress job={base} />);
    expect(screen.getByText("로컬 서재를 읽고 있습니다")).toBeInTheDocument();

    rerender(<JobProgress job={{...base, status: "failed", stage: "failed", error: "API 연결 실패"}} />);
    expect(screen.getByText("리서치를 완료하지 못했습니다")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("API 연결 실패");
  });
});
