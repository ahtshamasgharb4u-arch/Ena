import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { DailyLogModule } from './daily-log/daily-log.module';

@Module({
  imports: [DailyLogModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
