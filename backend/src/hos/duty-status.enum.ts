export enum DutyStatus {
  OFF_DUTY = 'OFF_DUTY',
  SLEEPER_BERTH = 'SLEEPER_BERTH',
  DRIVING = 'DRIVING',
  ON_DUTY_NOT_DRIVING = 'ON_DUTY_NOT_DRIVING',
}

export const DUTY_STATUSES = Object.values(DutyStatus);
export const QUARTER_HOUR_SLOTS = 96;
export const HOURS_PER_QUARTER = 0.25;
export const TEN_HOUR_OFF_SLOTS = 40; // 10h / 0.25
export const FOURTEEN_HOUR_ON_DUTY_WINDOW_SLOTS = 56; // 14h
export const THIRTY_MIN_OFF_SLOTS = 2;
