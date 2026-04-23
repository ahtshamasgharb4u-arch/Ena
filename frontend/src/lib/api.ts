const BASE =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE
    ? process.env.NEXT_PUBLIC_API_BASE
    : "http://localhost:3001/api";

export function apiUrl(path: string) {
  if (path.startsWith("/")) return `${BASE}${path}`;
  return `${BASE}/${path}`;
}

export async function fetchRecap(driverId: string, throughDate: string) {
  const q = new URLSearchParams({ driverId, throughDate });
  const r = await fetch(apiUrl(`/hos/recap?${q.toString()}`));
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || "Recap request failed");
  }
  return r.json() as Promise<{
    day70: { total7DaysWithToday: number; availableTomorrow70: number; total8DaysWithToday: number };
    day60: { total6DaysWithToday: number; availableTomorrow60: number; total7DaysWithToday: number };
    has34HourReset: boolean;
    note34?: string;
  }>;
}

export async function saveLog(body: object) {
  const r = await fetch(apiUrl("/daily-logs"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || "Save failed");
  }
  return r.json();
}

export async function loadLog(driverId: string, logDate: string) {
  const r = await fetch(
    apiUrl(
      `/daily-logs?${new URLSearchParams({ driverId, date: logDate })}`
    )
  );
  if (r.status === 404) {
    return null;
  }
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || "Load failed");
  }
  return r.json();
}
