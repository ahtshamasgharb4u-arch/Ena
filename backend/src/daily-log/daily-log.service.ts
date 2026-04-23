import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { DutyStatus, QUARTER_HOUR_SLOTS } from '../hos/duty-status.enum';
import { HosCalculationService, HOSDayAnalysis } from '../hos/hos-calculation.service';
import { UpsertDailyLogDto } from './dto/upsert-daily-log.dto';

export interface DailyLogEntity extends UpsertDailyLogDto {
  id: string;
  createdAt: string;
  updatedAt: string;
  analysis: HOSDayAnalysis;
}

@Injectable()
export class DailyLogService {
  private readonly store = new Map<string, DailyLogEntity>();
  private idSeq = 1;

  private key(driverId: string, logDate: string) {
    return `${driverId}::${logDate}`;
  }

  constructor(private readonly hos: HosCalculationService) {}

  upsert(dto: UpsertDailyLogDto): DailyLogEntity {
    if (dto.grid.length !== QUARTER_HOUR_SLOTS) {
      throw new BadRequestException(
        `The record of duty status must have ${QUARTER_HOUR_SLOTS} 15-minute intervals (full 24-hour graph).`,
      );
    }
    const v = this.hos.assertFullDayGrid(dto.grid);
    if (!v.ok) {
      throw new BadRequestException(v.error);
    }
    const analysis = this.hos.analyzeSingleDayGrid(v.duty);
    const k = this.key(dto.driverId, dto.logDate);
    const now = new Date().toISOString();
    const existing = this.store.get(k);
    const id = existing?.id ?? `log-${this.idSeq++}`;
    const row: DailyLogEntity = {
      ...dto,
      id,
      createdAt: existing?.createdAt ?? now,
      updatedAt: now,
      analysis,
    };
    this.store.set(k, row);
    return row;
  }

  findOne(driverId: string, logDate: string): DailyLogEntity {
    const e = this.store.get(this.key(driverId, logDate));
    if (!e) {
      throw new NotFoundException(`No daily log for that driver and date.`);
    }
    return e;
  }

  listByDriver(driverId: string) {
    const rows: DailyLogEntity[] = [];
    for (const e of this.store.values()) {
      if (e.driverId === driverId) rows.push(e);
    }
    return rows.sort((a, b) => a.logDate.localeCompare(b.logDate));
  }

  delete(driverId: string, logDate: string) {
    this.store.delete(this.key(driverId, logDate));
  }
}
