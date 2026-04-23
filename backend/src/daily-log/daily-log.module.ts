import { Module } from '@nestjs/common';
import { DailyLogController, HosRecapController } from './daily-log.controller';
import { DailyLogService } from './daily-log.service';
import { HosModule } from '../hos/hos.module';

@Module({
  imports: [HosModule],
  controllers: [DailyLogController, HosRecapController],
  providers: [DailyLogService],
  exports: [DailyLogService],
})
export class DailyLogModule {}
