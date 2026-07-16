"use client";

import {useId, useMemo, useState} from "react";

type ChipGroupProps = {
  label: string;
  description?: string;
  options: string[];
  value: string[];
  onChange: (value: string[]) => void;
  initialVisible?: number;
  maxSelected?: number;
  selectedCount?: number;
};

export function ChipGroup({
  label,
  description,
  options,
  value,
  onChange,
  initialVisible = 6,
  maxSelected,
  selectedCount = value.length,
}: ChipGroupProps) {
  const [expanded, setExpanded] = useState(false);
  const [limitHit, setLimitHit] = useState(false);
  const groupId = useId();
  const hiddenCount = options.slice(initialVisible).filter((option) => !value.includes(option)).length;
  const visibleOptions = useMemo(
    () => expanded ? options : options.filter((option, index) => index < initialVisible || value.includes(option)),
    [expanded, initialVisible, options, value],
  );

  const toggle = (option: string) => {
    const selected = value.includes(option);
    if (!selected && maxSelected != null && selectedCount >= maxSelected) {
      setLimitHit(true);
      return;
    }
    setLimitHit(false);
    onChange(selected ? value.filter((item) => item !== option) : [...value, option]);
  };

  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-semibold text-ink">{label}</legend>
      {description ? <p className="-mt-2 text-sm leading-5 text-muted">{description}</p> : null}
      <div id={groupId} className="flex flex-wrap gap-2">
        {visibleOptions.map((option) => {
          const selected = value.includes(option);
          return (
            <button
              key={option}
              type="button"
              aria-pressed={selected}
              onClick={() => toggle(option)}
              className="chip"
              data-selected={selected}
            >
              <span aria-hidden="true" className="chip-check">✓</span>
              {option}
            </button>
          );
        })}
      </div>
      {options.length > initialVisible ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <button
            type="button"
            className="chip-more"
            aria-expanded={expanded}
            aria-controls={groupId}
            onClick={() => {
              setExpanded((current) => !current);
              setLimitHit(false);
            }}
          >
            {expanded ? "간단히 보기" : `옵션 ${hiddenCount}개 더 보기`}
          </button>
          {maxSelected != null ? <span className="text-xs text-muted-soft">최대 {maxSelected}개</span> : null}
        </div>
      ) : null}
      {limitHit ? <p role="status" className="text-xs font-medium text-error">한 번에 최대 {maxSelected}개까지 선택할 수 있습니다.</p> : null}
    </fieldset>
  );
}
