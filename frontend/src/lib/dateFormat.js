/**
 * Format an ISO datetime string in Italian, ALWAYS in Europe/Rome timezone.
 *
 * Backend stores `data_ora` as UTC ISO (e.g. "2026-02-15T08:50:00+00:00") — the
 * therapist/patient must always see it as Rome local time regardless of the
 * device's timezone. Using `toLocaleString("it-IT")` without `timeZone` shows
 * the browser's local time, which caused visible offsets when a therapist
 * logged in from a device configured with the wrong timezone.
 */

const ROME_TZ = "Europe/Rome";

export function formatItalianDateTime(iso, opts = {}) {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat("it-IT", {
      timeZone: ROME_TZ,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      ...opts,
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatItalianTime(iso) {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat("it-IT", {
      timeZone: ROME_TZ,
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatItalianDate(iso, opts = {}) {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat("it-IT", {
      timeZone: ROME_TZ,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      ...opts,
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}
