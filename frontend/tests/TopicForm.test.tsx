import {render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";

import {TopicForm} from "@/features/research/TopicForm";

describe("TopicForm", () => {
  it("shows a validation error for an empty topic", async () => {
    const user = userEvent.setup();
    render(<TopicForm onSubmit={vi.fn()} />);

    await user.click(screen.getByRole("button", {name: "책과 근거 찾기"}));

    expect(screen.getByRole("alert")).toHaveTextContent("두 글자 이상의 영상 주제");
  });

  it("preserves the worker comfort-to-productivity direction in the API payload", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<TopicForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("영상 주제"), "일이 나를 삼키지 않게 하는 태도");
    await user.click(screen.getByRole("button", {name: "프리셋 적용"}));
    await user.click(screen.getByRole("button", {name: "책과 근거 찾기"}));

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      audience: "직장인",
      desired_emotional_effects: ["심리적 위로", "공감"],
      desired_lenses: ["심리학", "커리어", "생산성", "동기부여"],
      excluded_lenses: [],
    }));
  });

  it("expands diverse direction options and sends selected values", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<TopicForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("영상 주제"), "흔들릴 때 나를 이해하는 방법");

    const emotions = within(screen.getByRole("group", {name: "정서적 진입점"}));
    await user.click(emotions.getByRole("button", {name: /옵션 4개 더 보기/}));
    await user.click(emotions.getByRole("button", {name: "자기이해"}));

    const lenses = within(screen.getByRole("group", {name: "주요 관점"}));
    await user.click(lenses.getByRole("button", {name: /옵션 6개 더 보기/}));
    await user.click(lenses.getByRole("button", {name: "윤리"}));

    const expansions = within(screen.getByRole("group", {name: "후반부 확장"}));
    await user.click(expansions.getByRole("button", {name: /옵션 6개 더 보기/}));
    await user.click(expansions.getByRole("button", {name: "습관 설계"}));
    await user.click(screen.getByRole("button", {name: "책과 근거 찾기"}));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      desired_emotional_effects: ["공감", "위안", "자기이해"],
      desired_lenses: ["철학", "심리학", "윤리", "습관 설계"],
    }));
  });
});
