import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it} from "vitest";

import {ValidationResult} from "@/features/research/ValidationResult";

describe("ValidationResult", () => {
  it("shows issue severity, source lines, and report downloads", async () => {
    const user = userEvent.setup();
    render(<ValidationResult artifacts={{runId: "run_1", report: "# report", result: {
      status: "needs_revision", valid_count: 2, needs_review_count: 1, invalid_count: 1,
      issues: [{issue_id: "i1", severity: "high", category: "modified_quotation", section_id: "s2", paragraph_id: "p2", description: "인용문이 원문과 다릅니다.", recommended_action: "원문 문구를 사용합니다.", source_chunk_ids: ["c1"]}],
      citations: [{citation_id: "c1", paragraph_id: "p2", section_id: "s2", text_type: "quotation", text: "변경된 인용", book_ids: ["b1"], evidence_ids: ["e1"], status: "invalid", confidence: .42, review_summary: "원문 불일치", sources: [{chunk_id: "ch1", book_id: "b1", title: "일의 철학", author: "저자", source_file: "커리어/일의 철학.md", heading_path: ["2장", "일과 자아"], start_line: 21, end_line: 23, content_hash: "hash"}]}],
    }}} />);
    expect(screen.getByText("수정이 필요한 대본")).toBeInTheDocument();
    expect(screen.getByText("인용문 변경")).toBeInTheDocument();
    await user.click(screen.getAllByText(/s2 · p2/)[1]);
    expect(screen.getByText(/커리어\/일의 철학.md:21-23/)).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /검증 리포트/})).toHaveAttribute("href", expect.stringContaining("validation_report.md?download=true"));
  });
});
