import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";

import {ResearchResult} from "@/features/research/ResearchResult";

const candidates = [
  {book_id: "book-1", title: "행복론", author: "unknown", score: 0.91, chunk_count: 4, retrieval_score: 0.7, perspective: "삶의 철학", inclusion_reason: "행복과 자기이해의 구조를 설명한다."},
  {book_id: "book-2", title: "행복한 이기주의자", author: "웨인 다이어", score: 0.84, chunk_count: 3, retrieval_score: 0.6, perspective: "자기 가치", inclusion_reason: "타인의 평가와 자아를 분리한다."},
  {book_id: "book-3", title: "회복의 기술", author: "김회복", score: 0.81, chunk_count: 2, retrieval_score: 0.58, perspective: "회복", inclusion_reason: "회복의 단계를 설명한다."},
];

const selection = {
  selected_books: [{book_id: "book-1", role: "문제 구조 설명", selection_reason: "행복의 조건에 관한 근거가 명확하다."}, {book_id: "book-2", role: "자기 가치 회복", selection_reason: "타인의 평가와 자아를 분리한다."}],
  excluded_books: [{book_id: "book-3", reason: "역할 중복"}],
  cross_book_connection: "행복의 조건에서 자기 가치 회복으로 이어진다.",
};

describe("ResearchResult", () => {
  it("shows transparent candidate reasons and supports local selection", async () => {
    const user = userEvent.setup();
    const onGenerateOutline = vi.fn().mockResolvedValue(undefined);
    render(<ResearchResult candidates={candidates} selection={selection} onGenerateOutline={onGenerateOutline} />);

    expect(screen.getByText("행복과 자기이해의 구조를 설명한다.")).toBeInTheDocument();
    const third = screen.getByRole("button", {name: "회복의 기술 선택"});
    expect(third).toHaveAttribute("aria-pressed", "false");

    await user.click(third);

    expect(screen.getByRole("button", {name: "회복의 기술 선택 해제"})).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("3", {selector: "strong"}).parentElement).toHaveTextContent("3 / 4권 선택");

    await user.click(screen.getByRole("button", {name: "행복한 이기주의자 순서를 위로"}));
    await user.click(screen.getByRole("button", {name: /선택 확정/}));
    expect(onGenerateOutline).toHaveBeenCalledWith(["book-2", "book-1", "book-3"]);
  });
});
