import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col justify-center px-4 py-16">
      <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
        Hours of service &amp; daily log
      </h1>
      <p className="mt-3 text-base leading-relaxed text-zinc-600 dark:text-zinc-400">
        Full-stack assessment: FMCSA-style graph grid, remarks, 60/70-hour recap, and
        same-day 11- / 14- / 30-minute checks. Run the{" "}
        <span className="font-mono text-sm">backend</span> (Nest, port 3001) and this{" "}
        <span className="font-mono text-sm">frontend</span> (Next, port 3000).
      </p>
      <ul className="mt-8 space-y-3 text-base">
        <li>
          <Link
            className="font-medium text-sky-700 underline-offset-2 hover:underline dark:text-sky-400"
            href="/daily-log"
          >
            Driver&apos;s daily log
          </Link>{" "}
          — 24-hour graph, carrier and vehicle, remarks, recap.
        </li>
        <li>
          <Link
            className="font-medium text-sky-700 underline-offset-2 hover:underline dark:text-sky-400"
            href="/hos"
          >
            HOS reference
          </Link>{" "}
          — short guide (what is on duty, 11/14, 30 min, 60/70, 34h, ELD/RODS).
        </li>
      </ul>
    </div>
  );
}
