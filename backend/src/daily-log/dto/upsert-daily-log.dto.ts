import {
  ArrayMaxSize,
  ArrayMinSize,
  IsIn,
  IsInt,
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsString,
  IsArray,
  Min,
} from 'class-validator';
import { DUTY_STATUSES, QUARTER_HOUR_SLOTS, DutyStatus } from '../../hos/duty-status.enum';

export class UpsertDailyLogDto {
  @IsString()
  @IsNotEmpty()
  driverId!: string;

  /** YYYY-MM-DD, home terminal date */
  @IsString()
  @IsNotEmpty()
  logDate!: string;

  @IsInt()
  @Min(1)
  month!: number;

  @IsInt()
  @Min(1)
  day!: number;

  @IsInt()
  @Min(2000)
  year!: number;

  @IsString()
  fromRoute!: string;

  @IsString()
  toRoute!: string;

  @IsString()
  carrierName!: string;

  @IsString()
  mainOfficeAddress!: string;

  @IsString()
  homeTerminalAddress!: string;

  @IsNumber()
  @Min(0)
  totalMilesDriving!: number;

  @IsNumber()
  @Min(0)
  totalMileageToday!: number;

  @IsString()
  vehicleInfo!: string;

  /** 96 x 15-minute values, 24 hours, home terminal time */
  @IsArray()
  @ArrayMinSize(QUARTER_HOUR_SLOTS)
  @ArrayMaxSize(QUARTER_HOUR_SLOTS)
  @IsIn(DUTY_STATUSES, { each: true })
  grid!: DutyStatus[];

  @IsOptional()
  @IsString()
  remarks?: string;

  @IsOptional()
  @IsString()
  dvlOrManifestNo?: string;

  @IsOptional()
  @IsString()
  shipperCommodity?: string;

  /** Recap selection for UI only; 60/7 vs 70/8 */
  @IsOptional()
  @IsIn(['SIXTY_SEVEN', 'SEVENTY_EIGHT'])
  recapCycle?: 'SIXTY_SEVEN' | 'SEVENTY_EIGHT';
}
