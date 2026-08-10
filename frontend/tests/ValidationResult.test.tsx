import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";

import {ValidationResult} from "@/features/research/ValidationResult";

describe("ValidationResult", () => {
  it("shows issue severity, source lines, and report downloads", async () => {
    const user = userEvent.setup();
    const onRevise = vi.fn();
    render(<ValidationResult artifacts={{runId: "run_1", report: "# report", result: {
      status: "needs_revision", valid_count: 2, needs_review_count: 1, invalid_count: 1,
      issues: [{issue_id: "i1", severity: "high", category: "unsupported_paraphrase", section_id: "s2", paragraph_id: "p2", description: "요약이 원문보다 확대됐습니다.", recommended_action: "원문 범위로 문장을 완화합니다.", source_chunk_ids: ["c1"]}],
      citations: [{citation_id: "c1", paragraph_id: "p2", section_id: "s2", text_type: "paraphrase", text: "확대된 요약", book_ids: ["b1"], evidence_ids: ["e1"], status: "invalid", confidence: .42, review_summary: "원문보다 의미가 넓음", sources: [{chunk_id: "ch1", book_id: "b1", title: "행복론", author: "저자", source_file: "철학/행복론.md", heading_path: ["2장", "행복과 삶"], start_line: 21, end_line: 23, content_hash: "hash"}]}],
    }}} onRevise={onRevise} />);
    expect(screen.getByText("수정이 필요한 대본")).toBeInTheDocument();
    expect(screen.getByText("지원되지 않는 요약")).toBeInTheDocument();
    await user.click(screen.getAllByText(/s2 · p2/)[1]);
    expect(screen.getByText(/철학\/행복론.md:21-23/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", {name: "p2 문단 재작성 선택"})).toBeChecked();
    await user.click(screen.getByRole("button", {name: "재작성 후 다시 검증"}));
    expect(onRevise).toHaveBeenCalledWith(["p2"]);
    expect(screen.getByRole("link", {name: /검증 리포트/})).toHaveAttribute("href", expect.stringContaining("validation_report.md?download=true"));
  });
});
