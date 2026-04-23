"use client";

import { DUTY, DUTY_LABEL, DUTY_ORDER, DutyStatus, SLOTS, totals } from "@/lib/duty";
import { useCallback, useRef, useState } from "react";

const color: Record<DutyStatus, string> = {
  [DUTY.OFF_DUTY]: "var(--c-off, #d4d4d4)",
  [DUTY.SLEEPER_BERTH]: "var(--c-sb, #a5b4fc)",
  [DUTY.DRIVING]: "var(--c-dr, #facc15)",
  [DUTY.ON_DUTY_NOT_DRIVING]: "var(--c-od, #34d399)",
};

type Props = {
  grid: DutyStatus[];
  onChange: (g: DutyStatus[]) => void;
};

export function DutyGraphGrid({ grid, onChange }: Props) {
  const [brush, setBrush] = useState<DutyStatus>(DUTY.OFF_DUTY);
  const paint = useRef(false);
  const t = totals(grid);

  const apply = useCallback(
    (i: number, s: DutyStatus) => {
      if (i < 0 || i >= SLOTS) return;
      if (grid[i] === s) return;
      const n = grid.slice() as DutyStatus[];
      n[i] = s;
      onChange(n);
    },
    [grid, onChange]
  );

  const onPointerDown = (i: number) => {
    paint.current = true;
    apply(i, brush);
  };
  const onPointerEnter = (i: number) => {
    if (paint.current) apply(i, brush);
  };
  const stop = () => {
    paint.current = false;
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        A completed 24-hour graph: each column is 15 minutes (96 columns). Choose a
        line with the color buttons, then click or click-drag across the timeline to
        set when that duty applied (The graph grid, FMCSA form style).
      </p>
      <div className="flex flex-wrap gap-2">
        {DUTY_ORDER.map((d) => (
          <button
            type="button"
            key={d}
            onClick={() => setBrush(d)}
            className={`inline-flex items-center gap-2 rounded border px-3 py-1.5 text-sm font-medium transition ${
              brush === d
                ? "ring-2 ring-sky-500"
                : "ring-0"
            }`}
            style={{ background: color[d] }}
          >
            {DUTY_LABEL[d]}
          </button>
        ))}
      </div>
      <div
        className="select-none overflow-x-auto rounded border border-zinc-300 dark:border-zinc-700 p-1"
        onPointerLeave={stop}
        onPointerUp={stop}
        onPointerCancel={stop}
      >
        <div className="mb-1 flex justify-between text-[10px] font-mono text-zinc-500">
          <span>12 AM</span>
          <span>6</span>
          <span>12 (noon)</span>
          <span>6</span>
          <span>12 AM+1</span>
        </div>
        <div className="flex w-[min(100%,64rem)] min-w-full h-20 touch-none">
          {grid.map((c, i) => (
            <div
              key={i}
              onPointerDown={() => onPointerDown(i)}
              onPointerEnter={() => onPointerEnter(i)}
              className="min-w-[2px] flex-1 border-l border-zinc-400/30"
              style={{ background: color[c] }}
              title={`${(i * 0.25).toFixed(2)}h — ${DUTY_LABEL[c]}`}
            />
          ))}
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-sm">
        {DUTY_ORDER.map((d) => {
          const v = t;
          const num =
            d === DUTY.OFF_DUTY
              ? v.off
              : d === DUTY.SLEEPER_BERTH
                ? v.sb
                : d === DUTY.DRIVING
                  ? v.drive
                  : v.odn;
          return (
            <div key={d} className="rounded border border-zinc-200 px-2 py-1 dark:border-zinc-800">
              <div className="text-xs text-zinc-500">{DUTY_LABEL[d]}</div>
              <div className="font-mono text-lg">
                {num.toFixed(2)} <span className="text-xs">h</span>
              </div>
            </div>
          );
        })}
        <div className="rounded border border-zinc-900/20 bg-zinc-50 px-2 py-1 dark:border-zinc-600 dark:bg-zinc-900/40 sm:col-span-2 lg:col-span-1">
          <div className="text-xs text-zinc-500">On duty (lines 3+4) — recap</div>
          <div className="font-mono text-lg">
            {t.recap.toFixed(2)} <span className="text-xs">h</span>
          </div>
        </div>
      </div>
    </div>
  );
}
