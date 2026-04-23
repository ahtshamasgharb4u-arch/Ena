"use client";

import { DutyGraphGrid } from "@/components/DutyGraphGrid";
import { DUTY, makeEmptyGrid, type DutyStatus } from "@/lib/duty";
import { fetchRecap, loadLog, saveLog } from "@/lib/api";
import { useCallback, useEffect, useState } from "react";

function todayStr() {
  const d = new Date();
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const y = d.getFullYear();
  return {
    logDate: `${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
    month: m,
    day,
    year: y,
  };
}

export default function DailyLogPage() {
  const { logDate: defaultDate, month, day, year } = todayStr();
  const [driverId, setDriverId] = useState("driver-1");
  const [logDate, setLogDate] = useState(defaultDate);
  const [monthF, setMonthF] = useState(month);
  const [dayF, setDayF] = useState(day);
  const [yearF, setYearF] = useState(year);
  const [fromRoute, setFromRoute] = useState("");
  const [toRoute, setToRoute] = useState("");
  const [carrierName, setCarrierName] = useState("");
  const [mainOffice, setMainOffice] = useState("");
  const [homeTerminal, setHomeTerminal] = useState("");
  const [milesDr, setMilesDr] = useState(0);
  const [milesTotal, setMilesTotal] = useState(0);
  const [vehicleInfo, setVehicleInfo] = useState("");
  const [grid, setGrid] = useState<DutyStatus[]>(() => makeEmptyGrid(DUTY.OFF_DUTY));
  const [remarks, setRemarks] = useState("");
  const [dvl, setDvl] = useState("");
  const [ship, setShip] = useState("");
  const [recapCycle, setRecapCycle] = useState<"SIXTY_SEVEN" | "SEVENTY_EIGHT">(
    "SEVENTY_EIGHT"
  );
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [recap, setRecap] = useState<{
    day70: { total7DaysWithToday: number; availableTomorrow70: number; total8DaysWithToday: number };
    day60: { total6DaysWithToday: number; availableTomorrow60: number; total7DaysWithToday: number };
    has34HourReset: boolean;
    note34?: string;
  } | null>(null);
  const [serverAnalysis, setServerAnalysis] = useState<{
    violations: string[];
    warnings: string[];
  } | null>(null);

  const syncDateFields = (iso: string) => {
    const [y, m, d] = iso.split("-").map(Number);
    if (y && m && d) {
      setMonthF(m);
      setDayF(d);
      setYearF(y);
    }
  };

  const load = useCallback(async () => {
    setStatus(null);
    try {
      const r = await loadLog(driverId, logDate);
      if (!r) {
        setGrid(makeEmptyGrid(DUTY.OFF_DUTY));
        setServerAnalysis(null);
        return;
      }
      setMonthF(r.month);
      setDayF(r.day);
      setYearF(r.year);
      setFromRoute(r.fromRoute);
      setToRoute(r.toRoute);
      setCarrierName(r.carrierName);
      setMainOffice(r.mainOfficeAddress);
      setHomeTerminal(r.homeTerminalAddress);
      setMilesDr(r.totalMilesDriving);
      setMilesTotal(r.totalMileageToday);
      setVehicleInfo(r.vehicleInfo);
      setGrid(r.grid);
      setRemarks(r.remarks ?? "");
      setDvl(r.dvlOrManifestNo ?? "");
      setShip(r.shipperCommodity ?? "");
      if (r.recapCycle) setRecapCycle(r.recapCycle);
      setServerAnalysis({
        violations: r.analysis?.violations ?? [],
        warnings: r.analysis?.warnings ?? [],
      });
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Load error");
    }
  }, [driverId, logDate]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void (async () => {
      try {
        const c = await fetchRecap(driverId, logDate);
        setRecap(c);
      } catch {
        setRecap(null);
      }
    })();
  }, [driverId, logDate]);

  const onSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      const body = {
        driverId,
        logDate,
        month: monthF,
        day: dayF,
        year: yearF,
        fromRoute,
        toRoute,
        carrierName,
        mainOfficeAddress: mainOffice,
        homeTerminalAddress: homeTerminal,
        totalMilesDriving: milesDr,
        totalMileageToday: milesTotal,
        vehicleInfo,
        grid,
        remarks,
        dvlOrManifestNo: dvl,
        shipperCommodity: ship,
        recapCycle,
      };
      const r = await saveLog(body);
      setServerAnalysis({
        violations: r.analysis?.violations ?? [],
        warnings: r.analysis?.warnings ?? [],
      });
      try {
        setRecap(await fetchRecap(driverId, logDate));
      } catch {
        // ignore
      }
      setStatus("Saved. Record of duty status and remarks are on file for this 24-hour period.");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Save error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
        Driver&apos;s daily log (24 hours)
      </h1>
      <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
        Enter name of place you reported and where released; use the time standard of
        the home terminal. The graph must cover the full 24:00 in 15-minute rows.
      </p>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <label className="block text-sm">
          <span className="text-zinc-600">Driver id</span>
          <input
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={driverId}
            onChange={(e) => setDriverId(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="text-zinc-600">Log date (ISO)</span>
          <input
            type="date"
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={logDate}
            onChange={(e) => {
              setLogDate(e.target.value);
              syncDateFields(e.target.value);
            }}
          />
        </label>
        <div className="md:col-span-2 flex flex-wrap gap-3 text-sm">
          <label>
            Month
            <input
              type="number"
              className="ml-2 w-16 rounded border border-zinc-300 bg-white px-1 dark:border-zinc-700 dark:bg-zinc-950"
              value={monthF}
              onChange={(e) => setMonthF(Number(e.target.value))}
            />
          </label>
          <label>
            Day
            <input
              type="number"
              className="ml-2 w-16 rounded border border-zinc-300 bg-white px-1 dark:border-zinc-700 dark:bg-zinc-950"
              value={dayF}
              onChange={(e) => setDayF(Number(e.target.value))}
            />
          </label>
          <label>
            Year
            <input
              type="number"
              className="ml-2 w-20 rounded border border-zinc-300 bg-white px-1 dark:border-zinc-700 dark:bg-zinc-950"
              value={yearF}
              onChange={(e) => setYearF(Number(e.target.value))}
            />
          </label>
        </div>
        <label className="block text-sm">
          <span className="text-zinc-600">From</span>
          <input
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={fromRoute}
            onChange={(e) => setFromRoute(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="text-zinc-600">To</span>
          <input
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={toRoute}
            onChange={(e) => setToRoute(e.target.value)}
          />
        </label>
        <label className="block text-sm md:col-span-2">
          <span className="text-zinc-600">Name of carrier or carriers</span>
          <input
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={carrierName}
            onChange={(e) => setCarrierName(e.target.value)}
          />
        </label>
        <label className="block text-sm md:col-span-2">
          <span className="text-zinc-600">Main office address</span>
          <input
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={mainOffice}
            onChange={(e) => setMainOffice(e.target.value)}
          />
        </label>
        <label className="block text-sm md:col-span-2">
          <span className="text-zinc-600">Home terminal address</span>
          <input
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={homeTerminal}
            onChange={(e) => setHomeTerminal(e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="text-zinc-600">Total miles driving</span>
          <input
            type="number"
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={milesDr}
            onChange={(e) => setMilesDr(Number(e.target.value))}
          />
        </label>
        <label className="text-sm">
          <span className="text-zinc-600">Total mileage</span>
          <input
            type="number"
            className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={milesTotal}
            onChange={(e) => setMilesTotal(Number(e.target.value))}
          />
        </label>
        <label className="block text-sm md:col-span-2">
          <span className="text-zinc-600">Truck / trailer / license plate and state</span>
          <textarea
            className="mt-1 w-full min-h-16 rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
            value={vehicleInfo}
            onChange={(e) => setVehicleInfo(e.target.value)}
          />
        </label>
      </div>

      <section className="mt-10">
        <h2 className="text-lg font-medium">The graph grid</h2>
        <DutyGraphGrid grid={grid} onChange={setGrid} />
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-medium">Remarks</h2>
        <textarea
          className="mt-2 w-full min-h-24 rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
          placeholder="Where each change of duty happened; shipping notes…"
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
        />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="text-sm block">
            <span className="text-zinc-600">DVL or manifest no.</span>
            <input
              className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
              value={dvl}
              onChange={(e) => setDvl(e.target.value)}
            />
          </label>
          <label className="text-sm block">
            <span className="text-zinc-600">Shipper &amp; commodity</span>
            <input
              className="mt-1 w-full rounded border border-zinc-300 bg-white px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-950"
              value={ship}
              onChange={(e) => setShip(e.target.value)}
            />
          </label>
        </div>
      </section>

      {recap && (
        <section className="mt-10">
          <h2 className="text-lg font-medium">Recap — 70-hour / 8-day and 60-hour / 7-day</h2>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            Daily on-duty total is lines 3+4. Column B = hours you may be on duty
            tomorrow before hitting the 60- or 70-hour cap, without a 34-hour restart
            of off duty and/or consecutive sleeper-berth time.
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded border border-zinc-200 p-3 dark:border-zinc-800">
              <h3 className="font-medium">70 / 8</h3>
              <dl className="mt-2 space-y-1 text-sm">
                <div className="flex justify-between">
                  <dt>A: last 7 + today</dt>
                  <dd className="font-mono">{recap.day70.total7DaysWithToday.toFixed(2)} h</dd>
                </div>
                <div className="flex justify-between">
                  <dt>B: available next day (70−A)</dt>
                  <dd className="font-mono">{recap.day70.availableTomorrow70.toFixed(2)} h</dd>
                </div>
                <div className="flex justify-between">
                  <dt>C: last 8 + today</dt>
                  <dd className="font-mono">{recap.day70.total8DaysWithToday.toFixed(2)} h</dd>
                </div>
              </dl>
            </div>
            <div className="rounded border border-zinc-200 p-3 dark:border-zinc-800">
              <h3 className="font-medium">60 / 7</h3>
              <dl className="mt-2 space-y-1 text-sm">
                <div className="flex justify-between">
                  <dt>A: last 6 + today</dt>
                  <dd className="font-mono">{recap.day60.total6DaysWithToday.toFixed(2)} h</dd>
                </div>
                <div className="flex justify-between">
                  <dt>B: available next day (60−A)</dt>
                  <dd className="font-mono">{recap.day60.availableTomorrow60.toFixed(2)} h</dd>
                </div>
                <div className="flex justify-between">
                  <dt>C: last 7 + today</dt>
                  <dd className="font-mono">{recap.day60.total7DaysWithToday.toFixed(2)} h</dd>
                </div>
              </dl>
            </div>
          </div>
          <p className="mt-2 text-sm text-amber-800 dark:text-amber-200/90">
            34-hour rule: {recap.has34HourReset ? "This stored sequence shows 34+ consecutive off/SB at some point." : "Not shown as 34+ straight off/SB in stored logs; verify across two-day boundaries."} {recap.note34}
          </p>
          <label className="mt-2 block text-sm">
            <span className="text-zinc-600">Primary cycle for your operation</span>
            <select
              className="ml-2 rounded border border-zinc-300 bg-white px-2 py-1 dark:border-zinc-700 dark:bg-zinc-950"
              value={recapCycle}
              onChange={(e) =>
                setRecapCycle(e.target.value as "SIXTY_SEVEN" | "SEVENTY_EIGHT")
              }
            >
              <option value="SEVENTY_EIGHT">70 hours / 8 days</option>
              <option value="SIXTY_SEVEN">60 hours / 7 days</option>
            </select>
          </label>
        </section>
      )}

      {serverAnalysis && (
        <section className="mt-6 rounded border border-zinc-200 p-3 dark:border-zinc-800">
          <h3 className="font-medium">HOS check (illustrative, same day)</h3>
          {serverAnalysis.warnings.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-sm text-amber-900 dark:text-amber-100/90">
              {serverAnalysis.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
          {serverAnalysis.violations.length > 0 ? (
            <ul className="mt-2 list-disc pl-5 text-sm text-red-800 dark:text-red-200/90">
              {serverAnalysis.violations.map((v, i) => (
                <li key={i}>{v}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-emerald-800 dark:text-emerald-200/90">
              No automatic violations flagged for 11- / 14- / 30-minute rules in this
              24-hour graph. Cross-day sleeper berth splits and ELD data may still
              be required in production.
            </p>
          )}
        </section>
      )}

      <div className="mt-8 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onSave}
          disabled={saving}
          className="rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save & validate log"}
        </button>
        <button
          type="button"
          onClick={load}
          className="rounded border border-zinc-300 bg-white px-4 py-2 text-sm font-medium dark:border-zinc-700 dark:bg-zinc-950"
        >
          Reload from server
        </button>
        <button
          type="button"
          onClick={() => setGrid(makeEmptyGrid(DUTY.OFF_DUTY))}
          className="rounded border border-zinc-300 bg-white px-4 py-2 text-sm text-zinc-700 dark:border-zinc-700 dark:bg-zinc-950"
        >
          Clear graph
        </button>
      </div>
      {status && <p className="mt-3 text-sm text-zinc-700 dark:text-zinc-300">{status}</p>}
    </div>
  );
}
