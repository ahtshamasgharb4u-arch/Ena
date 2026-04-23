export const DUTY = {
  OFF_DUTY: "OFF_DUTY",
  SLEEPER_BERTH: "SLEEPER_BERTH",
  DRIVING: "DRIVING",
  ON_DUTY_NOT_DRIVING: "ON_DUTY_NOT_DRIVING",
} as const;

export type DutyStatus = (typeof DUTY)[keyof typeof DUTY];

export const SLOTS = 96;
export const QUARTER_H = 0.25;

export const DUTY_LABEL: Record<string, string> = {
  OFF_DUTY: "Off duty",
  SLEEPER_BERTH: "Sleeper berth",
  DRIVING: "Driving",
  ON_DUTY_NOT_DRIVING: "On duty (not driving)",
};

export const DUTY_ORDER: DutyStatus[] = [
  DUTY.OFF_DUTY,
  DUTY.SLEEPER_BERTH,
  DUTY.DRIVING,
  DUTY.ON_DUTY_NOT_DRIVING,
];

export function makeEmptyGrid(status: DutyStatus = DUTY.OFF_DUTY): DutyStatus[] {
  return Array(SLOTS).fill(status) as DutyStatus[];
}

export function totals(
  g: DutyStatus[]
): { off: number; sb: number; drive: number; odn: number; recap: number } {
  let off = 0;
  let sb = 0;
  let drive = 0;
  let odn = 0;
  for (const s of g) {
    if (s === DUTY.OFF_DUTY) off += QUARTER_H;
    else if (s === DUTY.SLEEPER_BERTH) sb += QUARTER_H;
    else if (s === DUTY.DRIVING) drive += QUARTER_H;
    else odn += QUARTER_H;
  }
  return { off, sb, drive, odn, recap: drive + odn };
}
