import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {useState} from "react";
import {describe, expect, it} from "vitest";

import {ChipGroup} from "@/components/ui/ChipGroup";

function LimitedGroup() {
  const [value, setValue] = useState<string[]>([]);
  return <ChipGroup label="선택 제한" options={["하나", "둘", "셋"]} value={value} onChange={setValue} maxSelected={2} />;
}

describe("ChipGroup", () => {
  it("announces the API selection limit without dropping current choices", async () => {
    const user = userEvent.setup();
    render(<LimitedGroup />);

    await user.click(screen.getByRole("button", {name: "하나"}));
    await user.click(screen.getByRole("button", {name: "둘"}));
    await user.click(screen.getByRole("button", {name: "셋"}));

    expect(screen.getByRole("status")).toHaveTextContent("최대 2개");
    expect(screen.getByRole("button", {name: "하나"})).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", {name: "셋"})).toHaveAttribute("aria-pressed", "false");
  });
});
