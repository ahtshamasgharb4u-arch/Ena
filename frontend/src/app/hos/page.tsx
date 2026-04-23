export default function HosReferencePage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 text-zinc-800 dark:text-zinc-200">
      <h1 className="text-2xl font-semibold tracking-tight">Interstate hours of service — short reference</h1>
      <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
        This app follows the same topics as FMCSA’s <em>Interstate Truck Driver’s Guide
        to Hours of Service</em> (educational summary; not legal advice).
      </p>

      <h2 className="text-lg font-medium">What are the hours of service (HOS) rules?</h2>
      <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
        They limit when and how long a commercial motor vehicle (CMV) driver may work
        and drive, to reduce fatigue-related risk. The rules apply to most interstate
        property and passenger carriers using vehicles over 10,001 lb GVWR, those
        carrying hazmat, and other covered operations. Intrastate rules can differ.
      </p>

      <h2 className="text-lg font-medium">Who must comply?</h2>
      <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
        Most drivers in interstate commerce, with limited exceptions. Personal use
        of a CMV, personal conveyance, and yard moves are special cases that ELDs
        may record with special duty categories.
      </p>

      <h2 className="text-lg font-medium">On duty vs. off duty</h2>
      <ul className="list-inside list-disc space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
        <li>
          <strong>On duty</strong> — time the driver is working for the carrier, or
          required to be ready to work; includes driving and on duty not driving.
        </li>
        <li>
          <strong>Off duty</strong> — time when the driver is not working and is free
          to use time for their own purposes.
        </li>
        <li>
          <strong>Sleeper berth</strong> — rest in the sleeper; often paired with
          other off duty for split-sleeper patterns (8/2, etc., per current rules and
          training).
        </li>
      </ul>

      <h2 className="text-lg font-medium">Core property limits (typical 11/14 / 8 / 30 / 60·70 / 34)</h2>
      <ul className="list-inside list-disc space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
        <li>
          <strong>11-hour driving</strong> — at most 11 hours of driving after 10
          consecutive hours off duty and/or in the sleeper.
        </li>
        <li>
          <strong>14-hour on-duty window</strong> — you may not drive after the 14th
          hour of coming on duty (after 10+ hours off) until you take a new
          qualifying 10+ hour break, subject to the specific rule text in effect
          for your operation.
        </li>
        <li>
          <strong>30-minute break</strong> — after 8 total hours of driving, take 30
          consecutive minutes off duty and/or in the sleeper before more driving
          (property; certain short-haul and other cases may differ).
        </li>
        <li>
          <strong>60/70 hour rules</strong> — 60 on-duty hours in 7 days (or 70 in
          8 days) depending on your carrier’s schedule; a rolling total of on-duty
          time (driving + on duty not driving) in the form’s recap.
        </li>
        <li>
          <strong>70 hours / 8 days</strong> — “rolling 8” total of on duty time;
          the paper recap column C is the 8-day total; column A is 7 days + today
          for the 70-hour table.
        </li>
        <li>
          <strong>34-hour restart</strong> — 34 consecutive off-duty and/or
          consecutive sleeper-berth hours can restart the 60/70-hour clock, when
          allowed by current rules and company policy.
        </li>
        <li>
          <strong>Sleeper berth provision</strong> — may allow pairing off-duty
          and sleeper periods when done per current regulation; this demo does not
          model every split.
        </li>
      </ul>

      <h2 className="text-lg font-medium">ELD and the record of duty status (RODS)</h2>
      <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
        A <strong>driver’s daily log</strong> (paper or <strong>ELD</strong>) must
        show the full 24 hours, home terminal time, the graph (or ELD event list),
        total miles, carrier and vehicle, and <strong>remarks</strong> explaining
        changes. A <strong>completed grid</strong> and <strong>completed log</strong>{" "}
        means no gaps and a clear story of the day.
      </p>

      <p className="text-sm text-zinc-500">
        Use the <a className="text-sky-600 underline" href="/daily-log">Daily log</a> screen to build a 24-hour graph
        and recap; the API runs basic same-day HOS checks.
      </p>
    </div>
  );
}
