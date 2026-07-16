import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {describe, expect, it, vi} from "vitest";

import {ScriptResult} from "@/features/research/ScriptResult";

describe("ScriptResult", () => {
  it("toggles internal sources and exposes both downloads", async () => {
    const user = userEvent.setup();
    const onValidate = vi.fn().mockResolvedValue(undefined);
    render(<ScriptResult artifacts={{runId: "run_1", clean: "# 제목\n\n깨끗한 대본", sourced: "# 제목\n\n[SOURCE:e_1]"}} onValidate={onValidate} />);
    expect(screen.getByText(/깨끗한 대본/)).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", {name: "내부 출처 표시"}));
    expect(screen.getByText(/SOURCE:e_1/)).toBeInTheDocument();
    expect(screen.getByRole("link", {name: /대본 다운로드/})).toHaveAttribute("href", expect.stringContaining("script.md?download=true"));
    expect(screen.getByRole("link", {name: /출처 포함/})).toHaveAttribute("href", expect.stringContaining("script_with_sources.md?download=true"));
    await user.click(screen.getByRole("button", {name: /Phase 7 출처 검증/}));
    expect(onValidate).toHaveBeenCalledOnce();
  });
});
