import { Injectable } from '@nestjs/common';
import {
  DutyStatus,
  FOURTEEN_HOUR_ON_DUTY_WINDOW_SLOTS,
  HOURS_PER_QUARTER,
  QUARTER_HOUR_SLOTS,
  TEN_HOUR_OFF_SLOTS,
  THIRTY_MIN_OFF_SLOTS,
} from './duty-status.enum';

export interface DayTotals {
  offDuty: number;
  sleeper: number;
  driving: number;
  onDutyNotDriving: number;
  /** Line 3 + 4: used for 60/70-hour recap. */
  onDutyForRecap: number;
}

export interface HOSDayAnalysis {
  totals: DayTotals;
  violations: string[];
  warnings: string[];
  hasQualifying30Break: boolean;
}

@Injectable()
export class HosCalculationService {
  isRestSlot(status: DutyStatus): boolean {
    return status === DutyStatus.OFF_DUTY || status === DutyStatus.SLEEPER_BERTH;
  }

  isDriving(status: DutyStatus): boolean {
    return status === DutyStatus.DRIVING;
  }

  getTotalsFromGrid(grid: DutyStatus[]): DayTotals {
    let offDuty = 0;
    let sleeper = 0;
    let driving = 0;
    let onDutyNotDriving = 0;
    for (const s of grid) {
      const h = HOURS_PER_QUARTER;
      switch (s) {
        case DutyStatus.OFF_DUTY:
          offDuty += h;
          break;
        case DutyStatus.SLEEPER_BERTH:
          sleeper += h;
          break;
        case DutyStatus.DRIVING:
          driving += h;
          break;
        case DutyStatus.ON_DUTY_NOT_DRIVING:
          onDutyNotDriving += h;
          break;
      }
    }
    return {
      offDuty,
      sleeper,
      driving,
      onDutyNotDriving,
      onDutyForRecap: driving + onDutyNotDriving,
    };
  }

  assertFullDayGrid(
    grid: string[],
  ): { ok: true; duty: DutyStatus[] } | { ok: false; error: string } {
    if (!Array.isArray(grid) || grid.length !== QUARTER_HOUR_SLOTS) {
      return {
        ok: false,
        error: `Grid must be exactly ${QUARTER_HOUR_SLOTS} 15-minute slots (24 hours).`,
      };
    }
    const duty: DutyStatus[] = [];
    for (const g of grid) {
      if (!Object.values(DutyStatus).includes(g as DutyStatus)) {
        return { ok: false, error: `Invalid duty status: ${g}` };
      }
      duty.push(g as DutyStatus);
    }
    return { ok: true, duty };
  }

  analyzeSingleDayGrid(grid: DutyStatus[]): HOSDayAnalysis {
    const violations: string[] = [];
    const warnings: string[] = [];
    const totals = this.getTotalsFromGrid(grid);

    if (grid.length !== QUARTER_HOUR_SLOTS) {
      violations.push('The duty graph must have 96 15-minute rows covering 24:00 in home terminal time.');
      return { totals, violations, warnings, hasQualifying30Break: true };
    }

    this.checkShift11And14(grid, warnings, violations);
    const br = this.check8HourBreakRule(grid);
    if (br.violations.length) {
      violations.push(...br.violations);
    }

    return {
      totals,
      violations: [...new Set(violations)],
      warnings: [...new Set(warnings)],
      hasQualifying30Break: br.qualified,
    };
  }

  private checkShift11And14(
    grid: DutyStatus[],
    warnings: string[],
    violations: string[],
  ) {
    const totals = this.getTotalsFromGrid(grid);
    if (totals.driving - 1e-6 > 11) {
      violations.push(
        'The log shows more than 11 total hours in the Driving row. Federal property rules cap driving at 11 hours after 10+ consecutive off-duty hours, within a 14-hour on-duty period.',
      );
    }

    let i = 0;
    let rest = 0;
    while (i < QUARTER_HOUR_SLOTS) {
      while (i < QUARTER_HOUR_SLOTS && this.isRestSlot(grid[i]!)) {
        rest++;
        i++;
      }
      if (i >= QUARTER_HOUR_SLOTS) break;
      if (rest < TEN_HOUR_OFF_SLOTS) {
        warnings.push(
          'Fewer than 10 consecutive off-duty and/or sleeper hours appear immediately before an on-duty block. A prior 24-hour log is needed to show rest that was finished before midnight.',
        );
      }

      const shiftStart = i;
      let j = i;
      let driveIn14Window = 0;
      while (j < QUARTER_HOUR_SLOTS) {
        if (this.isRestSlot(grid[j]!)) {
          let r = 0;
          while (j < QUARTER_HOUR_SLOTS && this.isRestSlot(grid[j]!)) {
            r++;
            j++;
          }
          if (r >= TEN_HOUR_OFF_SLOTS) {
            if (driveIn14Window - 1e-6 > 11) {
              violations.push(
                'More than 11 hours of driving in a 14-hour on-duty window (11-hour limit).',
              );
            }
            i = j;
            rest = 0;
            break;
          }
          if (j >= QUARTER_HOUR_SLOTS) break;
          continue;
        }

        const slotsIntoShift = j - shiftStart;
        if (this.isDriving(grid[j]!)) {
          if (slotsIntoShift >= FOURTEEN_HOUR_ON_DUTY_WINDOW_SLOTS) {
            violations.push(
              'Driving is shown at or after 14 hours of clock time from the start of a workday without a new 10+ hours off. No driving is allowed after the 14th hour in that period (14-hour rule).',
            );
          } else {
            driveIn14Window += HOURS_PER_QUARTER;
          }
        }
        j++;
      }
      if (j >= QUARTER_HOUR_SLOTS) {
        if (driveIn14Window - 1e-6 > 11) {
          violations.push(
            'More than 11 hours of driving in a 14-hour on-duty window (11-hour limit).',
          );
        }
        break;
      }
    }
  }

  private check8HourBreakRule(grid: DutyStatus[]): { violations: string[]; qualified: boolean } {
    const violations: string[] = [];
    let drivingSince30 = 0;
    let consecutiveOffSb = 0;
    for (const status of grid) {
      if (this.isRestSlot(status)) {
        consecutiveOffSb += 1;
        if (consecutiveOffSb >= THIRTY_MIN_OFF_SLOTS) {
          drivingSince30 = 0;
        }
        continue;
      }
      consecutiveOffSb = 0;
      if (this.isDriving(status)) {
        drivingSince30 += HOURS_PER_QUARTER;
        if (drivingSince30 - 1e-6 > 8) {
          violations.push(
            'The 30-minute break rule: after 8 total hours of driving, take at least 30 consecutive minutes off duty or in the sleeper berth before further driving (property).',
          );
          break;
        }
      }
    }
    return { violations, qualified: !violations.length };
  }

  /**
   * 70/8 and 60/7 recap for completed daily totals (on-duty = lines 3+4) ordered oldest to newest, including today.
   */
  recapRolling(
    onDutyByDateChronological: { date: string; onDuty: number }[],
  ): {
    day70: { total7DaysWithToday: number; availableTomorrow70: number; total8DaysWithToday: number };
    day60: { total6DaysWithToday: number; availableTomorrow60: number; total7DaysWithToday: number };
  } {
    const rows = onDutyByDateChronological;
    const n = rows.length;
    const sumLast = (k: number) => {
      if (n === 0) return 0;
      const c = Math.min(k, n);
      let s = 0;
      for (let j = n - c; j < n; j++) s += rows[j]!.onDuty;
      return s;
    };
    return {
      day70: {
        total7DaysWithToday: sumLast(7),
        availableTomorrow70: Math.max(0, 70 - sumLast(7)),
        total8DaysWithToday: sumLast(8),
      },
      day60: {
        total6DaysWithToday: sumLast(6),
        availableTomorrow60: Math.max(0, 60 - sumLast(6)),
        total7DaysWithToday: sumLast(7),
      },
    };
  }

  /** 34+ consecutive off duty or sleeper, measured in 15-minute slots, across one or more consecutive daily grids. */
  has34HourReset(gridsChronological: DutyStatus[][]): boolean {
    let runQ = 0;
    for (const grid of gridsChronological) {
      for (const s of grid) {
        if (this.isRestSlot(s)) {
          runQ += 1;
          if (runQ * HOURS_PER_QUARTER >= 34 - 1e-9) return true;
        } else {
          runQ = 0;
        }
      }
    }
    return false;
  }
}
