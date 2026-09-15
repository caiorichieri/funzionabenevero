/**
 * Extract a human-readable string from an axios error response.
 * FastAPI 422 returns `detail` as an ARRAY of Pydantic error objects
 * (`{type, loc, msg, input, ctx, url}`), which crashes React when
 * rendered as a JSX child (React error #31 / blank screen).
 *
 * This helper always returns a plain string, safe to use with setState
 * and to render directly inside JSX.
 */
export function formatApiError(err, fallback = "Errore imprevisto") {
  const detail = err?.response?.data?.detail;
  if (!detail) return err?.message || fallback;

  // Common case: string (custom HTTPException from our routers)
  if (typeof detail === "string") return detail;

  // FastAPI 422 validation errors: array of {loc, msg, type, ...}
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        if (typeof e === "string") return e;
        const field = Array.isArray(e?.loc) ? e.loc.filter((x) => x !== "body").join(".") : "";
        const msg = e?.msg || "valore non valido";
        return field ? `${field}: ${msg}` : msg;
      })
      .join(" · ");
  }

  // Object (rare): flatten known fields
  if (typeof detail === "object") {
    if (typeof detail.msg === "string") return detail.msg;
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }

  return String(detail);
}
