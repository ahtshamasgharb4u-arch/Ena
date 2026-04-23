import {
  BadRequestException,
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Post,
  Query,
} from '@nestjs/common';
import { DailyLogService } from './daily-log.service';
import { UpsertDailyLogDto } from './dto/upsert-daily-log.dto';
import { DutyStatus } from '../hos/duty-status.enum';
import { HosCalculationService } from '../hos/hos-calculation.service';

@Controller('daily-logs')
export class DailyLogController {
  constructor(private readonly dailyLog: DailyLogService) {}

  @Get()
  list(@Query('driverId') driverId: string, @Query('date') date: string | undefined) {
    if (!driverId) {
      throw new BadRequestException('driverId is required');
    }
    if (date) {
      return this.dailyLog.findOne(driverId, date);
    }
    return this.dailyLog.listByDriver(driverId);
  }

  @Post()
  create(@Body() body: UpsertDailyLogDto) {
    return this.dailyLog.upsert(body);
  }

  @Delete(':driverId/:date')
  remove(@Param('driverId') driverId: string, @Param('date') date: string) {
    this.dailyLog.delete(decodeURIComponent(driverId), date);
    return { ok: true };
  }
}

@Controller('hos')
export class HosRecapController {
  constructor(
    private readonly dailyLog: DailyLogService,
    private readonly hos: HosCalculationService,
  ) {}

  @Get('recap')
  recap(
    @Query('driverId') driverId: string,
    @Query('throughDate') throughDate: string,
  ) {
    if (!driverId || !throughDate) {
      return {
        error: 'driverId and throughDate (YYYY-MM-DD) are required',
      };
    }
    const all = this.dailyLog
      .listByDriver(driverId)
      .filter((r) => r.logDate <= throughDate);
    if (!all.length) {
      return {
        driverId,
        throughDate,
        day70: {
          total7DaysWithToday: 0,
          availableTomorrow70: 70,
          total8DaysWithToday: 0,
        },
        day60: {
          total6DaysWithToday: 0,
          availableTomorrow60: 60,
          total7DaysWithToday: 0,
        },
        onDutyByDate: [] as { date: string; onDuty: number }[],
        has34HourReset: false,
        note34:
          'A 34-hour off-duty and/or consecutive sleeper-berth restart of the weekly clock requires 34 consecutive off-duty and/or SB hours, often checked across more than one daily log (34-hour restart).',
      };
    }
    const onDutyByDate = all.map((r) => ({
      date: r.logDate,
      onDuty: r.analysis.totals.onDutyForRecap,
    }));
    const rolling = this.hos.recapRolling(onDutyByDate);
    const grids = all.map((r) => r.grid as DutyStatus[]);
    return {
      driverId,
      throughDate,
      day70: rolling.day70,
      day60: rolling.day60,
      onDutyByDate,
      has34HourReset: this.hos.has34HourReset(grids),
      note34:
        'A 34-hour off-duty and/or consecutive sleeper-berth restart of the weekly clock requires 34 consecutive off-duty and/or SB hours, often checked across more than one daily log (34-hour restart).',
    };
  }
}
