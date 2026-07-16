"use client";

import {FormEvent, useMemo, useState} from "react";
import {ArrowRight, BriefcaseBusiness, Sparkles} from "lucide-react";

import {ChipGroup} from "@/components/ui/ChipGroup";
import {SegmentedControl} from "@/components/ui/SegmentedControl";
import type {ResearchRequest} from "@/types/api";

const EMOTIONS = [
  "심리적 위로", "위안", "공감", "안도", "호기심", "용기", "희망", "자기이해", "문제의식", "경각심",
];
const LENSES = [
  "철학", "심리학", "사회학", "커리어", "관계", "뇌과학", "문화", "역사", "윤리", "교육", "경제", "조직",
];
const EXPANSIONS = [
  "생산성", "동기부여", "실천 방법", "업무 경계", "관계 회복", "자기돌봄", "습관 설계", "감정 조절", "의사결정", "커뮤니케이션", "리더십", "삶의 의미",
];
const EXCLUSIONS = ["조직관리", "성과 압박", "투자", "종교적 해석"];

type FormState = {
  topic: string;
  duration: number;
  books: number;
  tone: string;
  audience: string;
  emotions: string[];
  lenses: string[];
  expansions: string[];
  exclusions: string[];
};

const DEFAULT_STATE: FormState = {
  topic: "",
  duration: 12,
  books: 3,
  tone: "사색적",
  audience: "일반 성인",
  emotions: ["공감", "위안"],
  lenses: ["철학", "심리학"],
  expansions: [],
  exclusions: [],
};

const WORKER_PRESET: Partial<FormState> = {
  audience: "직장인",
  emotions: ["심리적 위로", "공감"],
  lenses: ["심리학", "커리어"],
  expansions: ["생산성", "동기부여"],
  exclusions: [],
};

type TopicFormProps = {
  disabled?: boolean;
  onSubmit: (request: ResearchRequest) => Promise<void> | void;
};

export function TopicForm({disabled = false, onSubmit}: TopicFormProps) {
  const [form, setForm] = useState(DEFAULT_STATE);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lensSelectionCount = new Set([...form.lenses, ...form.expansions]).size;

  const directionSummary = useMemo(() => {
    const opening = form.emotions.length ? form.emotions.join("·") : "차분한 문제의식";
    const middle = form.lenses.length ? form.lenses.join("·") : "도서 근거";
    const ending = form.expansions.length ? `${form.expansions.join("·")}로 확장` : "성찰로 마무리";
    return `${form.audience}에게 ${opening}에서 출발해 ${middle} 관점으로 설명하고, ${ending}합니다.`;
  }, [form]);

  const patch = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((current) => ({...current, [key]: value}));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const topic = form.topic.trim();
    if (topic.length < 2) {
      setError("두 글자 이상의 영상 주제를 입력해 주세요.");
      return;
    }
    setError(null);
    await onSubmit({
      topic,
      duration_minutes: form.duration,
      target_book_count: form.books,
      tone: form.tone,
      audience: form.audience.trim() || "일반 성인",
      desired_lenses: [...new Set([...form.lenses, ...form.expansions])],
      desired_emotional_effects: form.emotions,
      excluded_lenses: form.exclusions,
    });
  };

  return (
    <form onSubmit={submit} className="workspace-card p-5 sm:p-7 lg:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">새 리서치</p>
          <h2 className="mt-2 text-[22px] font-semibold tracking-[-0.02em] text-ink">어떤 이야기를 만들까요?</h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted">대본보다 먼저 책과 근거를 찾습니다. 원하는 정서와 관점을 구체적으로 알려주세요.</p>
        </div>
        <span className="hidden rounded-full bg-[#fff1f3] p-3 text-primary sm:block" aria-hidden="true">
          <Sparkles size={20} />
        </span>
      </div>

      <div className="mt-7">
        <label htmlFor="topic" className="text-sm font-semibold text-ink">영상 주제</label>
        <textarea
          id="topic"
          value={form.topic}
          onChange={(event) => patch("topic", event.target.value)}
          placeholder="예: 일이 나를 삼키지 않게 하는 커리어의 태도"
          rows={3}
          disabled={disabled}
          aria-describedby={error ? "topic-error" : "topic-hint"}
          aria-invalid={Boolean(error)}
          className="text-area mt-2"
        />
        {error ? <p id="topic-error" role="alert" className="mt-2 text-sm text-error">{error}</p> : <p id="topic-hint" className="mt-2 text-xs text-muted">질문형 또는 설명형 주제를 모두 사용할 수 있습니다.</p>}
      </div>

      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        <SegmentedControl label="영상 길이" value={form.duration} onChange={(value) => patch("duration", value)} options={[{label: "8분", value: 8}, {label: "12분", value: 12}, {label: "20분", value: 20}]} />
        <SegmentedControl label="도서 수" value={form.books} onChange={(value) => patch("books", value)} options={[{label: "2권", value: 2}, {label: "3권", value: 3}, {label: "4권", value: 4}]} />
      </div>

      <section className="preset-card mt-7" aria-labelledby="audience-preset-title">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 rounded-full bg-white p-2 text-primary shadow-sm" aria-hidden="true"><BriefcaseBusiness size={18} /></span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p id="audience-preset-title" className="text-sm font-semibold text-ink">직장인 프리셋</p>
                <p className="mt-1 text-sm leading-5 text-muted">심리적 위로와 공감에서 시작해 생산성·동기부여로 확장합니다.</p>
              </div>
              <button type="button" className="secondary-button compact" onClick={() => setForm((current) => ({...current, ...WORKER_PRESET}))}>프리셋 적용</button>
            </div>
            <p className="mt-3 text-xs leading-5 text-muted-soft">적용 항목: 타겟 직장인 · 심리학/커리어 · 생산성/동기부여 · 제외 관점 없음</p>
          </div>
        </div>
      </section>

      <div className="mt-7 grid gap-6">
        <div>
          <label htmlFor="audience" className="text-sm font-semibold text-ink">타겟 시청자</label>
          <input id="audience" value={form.audience} onChange={(event) => patch("audience", event.target.value)} className="text-input mt-2" />
        </div>
        <ChipGroup label="정서적 진입점" description="시청자가 처음 느끼게 될 감정입니다." options={EMOTIONS} value={form.emotions} onChange={(value) => patch("emotions", value)} maxSelected={8} />
        <ChipGroup label="주요 관점" description="책을 찾고 해석할 중심 렌즈입니다." options={LENSES} value={form.lenses} onChange={(value) => patch("lenses", value)} maxSelected={8} selectedCount={lensSelectionCount} />
        <ChipGroup label="후반부 확장" description="문제 이해 뒤에 연결할 실용적인 방향입니다." options={EXPANSIONS} value={form.expansions} onChange={(value) => patch("expansions", value)} maxSelected={8} selectedCount={lensSelectionCount} />
      </div>

      <button type="button" className="mt-7 text-sm font-semibold text-ink underline decoration-hairline underline-offset-4" aria-expanded={showAdvanced} onClick={() => setShowAdvanced((value) => !value)}>
        {showAdvanced ? "세부 설정 접기" : "톤과 제외 관점 설정"}
      </button>

      {showAdvanced ? (
        <div className="mt-5 grid gap-6 border-t border-hairline-soft pt-6">
          <SegmentedControl label="톤" value={form.tone} onChange={(value) => patch("tone", value)} options={[{label: "사색적", value: "사색적"}, {label: "지적", value: "지적"}, {label: "실용적", value: "실용적"}, {label: "스토리", value: "스토리텔링"}]} />
          <ChipGroup label="제외할 관점" description="이번 영상에서 의도적으로 다루지 않을 문맥입니다." options={EXCLUSIONS} value={form.exclusions} onChange={(value) => patch("exclusions", value)} />
        </div>
      ) : null}

      <div className="direction-summary mt-7">
        <p className="eyebrow">영상 방향 미리보기</p>
        <p className="mt-2 text-sm leading-6 text-ink">{directionSummary}</p>
      </div>

      <button type="submit" disabled={disabled} className="primary-button mt-6 w-full sm:w-auto">
        {disabled ? "리서치 진행 중" : "책과 근거 찾기"}
        <ArrowRight size={18} aria-hidden="true" />
      </button>
    </form>
  );
}
