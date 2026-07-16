import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";

import {OutlineResult} from "@/features/research/OutlineResult";

describe("OutlineResult", () => {
  it("shows narrative context and submits edited title and sections", async () => {
    const user = userEvent.setup();
    const onGenerateScript = vi.fn().mockResolvedValue(undefined);
    render(<OutlineResult
      candidates={[{book_id: "a", title: "일의 철학", author: "저자", score: .9, chunk_count: 2, retrieval_score: .8}]}
      selection={{selected_books: [{book_id: "a", role: "문제 정의", selection_reason: "근거"}, {book_id: "b", role: "회복", selection_reason: "근거"}], excluded_books: [], cross_book_connection: "연결"}}
      plan={{title_candidates: ["일이 나를 삼키지 않게", "성과와 나 사이", "일에서 나를 되찾는 법"], core_message: "일은 나의 전부가 아니다.", emotional_arc: ["압박", "이해", "안도"], total_seconds: 600, sections: [
        {section_id: "hook", title: "퇴근해도 끝나지 않는 일", narrative_function: "hook", purpose: "감정에 진입한다.", key_points: ["압박"], book_ids: [], evidence_ids: [], estimated_seconds: 30},
        {section_id: "problem", title: "일과 자아", narrative_function: "problem", purpose: "문제를 설명한다.", key_points: ["분리"], book_ids: ["a"], evidence_ids: ["e1"], estimated_seconds: 120},
        {section_id: "perspective", title: "새 관점", narrative_function: "book_perspective", purpose: "관점을 제시한다.", key_points: ["관점"], book_ids: ["a"], evidence_ids: ["e1"], estimated_seconds: 120},
        {section_id: "integration", title: "통합", narrative_function: "integration", purpose: "두 관점을 잇는다.", key_points: ["통합"], book_ids: ["a"], evidence_ids: ["e1"], estimated_seconds: 180},
        {section_id: "conclusion", title: "마무리", narrative_function: "conclusion", purpose: "질문을 남긴다.", key_points: ["질문"], book_ids: [], evidence_ids: [], estimated_seconds: 150},
      ]}}
      onGenerateScript={onGenerateScript}
    />);
    expect(screen.getByText("일은 나의 전부가 아니다.")).toBeInTheDocument();
    expect(screen.getByText("성과와 나 사이")).toBeInTheDocument();
    expect(screen.getByText("안도")).toBeInTheDocument();
    expect(screen.getAllByText(/잠긴 근거 도서 · 일의 철학/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("배정 2분 0초")).toHaveLength(2);

    await user.click(screen.getByRole("radio", {name: /성과와 나 사이/}));
    const purpose = screen.getByLabelText("이 섹션의 목적", {selector: "#section-purpose-problem"});
    await user.clear(purpose);
    await user.type(purpose, "성과와 자아의 결합을 설명한다.");
    await user.click(screen.getByRole("button", {name: "새 관점 섹션을 위로"}));
    await user.click(screen.getByRole("button", {name: /구성안 확정/}));
    expect(onGenerateScript).toHaveBeenCalledWith(expect.objectContaining({selected_title: "성과와 나 사이"}));
    expect(onGenerateScript.mock.calls[0][0].sections.map((item: {section_id: string}) => item.section_id)).toEqual(["hook", "perspective", "problem", "integration", "conclusion"]);
    expect(onGenerateScript.mock.calls[0][0].sections[2].purpose).toBe("성과와 자아의 결합을 설명한다.");
  });
});
