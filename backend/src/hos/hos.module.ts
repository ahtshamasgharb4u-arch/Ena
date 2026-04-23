import { Module } from '@nestjs/common';
import { HosCalculationService } from './hos-calculation.service';

@Module({
  providers: [HosCalculationService],
  exports: [HosCalculationService],
})
export class HosModule {}
