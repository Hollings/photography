/**
 * Extract the numeric aperture (e.g. “1.8”) from a lens description string.
 * Returns an empty string if no aperture is found or the input is not a string.
 */
export function extractAperture(lens) {
  if (typeof lens !== "string") return "";
  const match = lens.match(/f\/?(\d+(?:\.\d+)?)/i);
  return match ? match[1] : "";
}

/**
 * Format a shutter speed expressed in fractional seconds
 * (e.g. "1/2000") into a user‑friendly string.
 */
export function formatShutter(shutter) {
  if (!shutter) return "";
  // already in a fractional form – just return
  if (shutter.includes("/")) return shutter;

  // handle decimal seconds (e.g. "0.005")
  const value = parseFloat(shutter);
  if (Number.isNaN(value) || value <= 0) return "";

  return value >= 1
    ? `${value.toFixed(1)} s`
    : `1/${Math.round(1 / value)}`;
}

/**
 * Map an S3 URL to a proxied path on this domain.
 * If the URL looks like an AWS S3 URL, return "/images/<key>".
 * Otherwise return the URL unchanged.
 */
export function viaCee(url) {
  if (!url) return url;
  const isDev = typeof window !== "undefined" && /^(localhost|127\.0\.0\.1)$/i.test(window.location.hostname);
  if (isDev) return url; // keep absolute S3 URLs during local dev
  try {
    const u = new URL(url);
    if (u.hostname.includes("amazonaws.com")) {
      // Keep the path as-is; Nginx will strip the /images/ prefix and proxy to S3
      return `/images${u.pathname}`;
    }
    return url;
  } catch (_) {
    // not an absolute URL – return as-is
    return url;
  }
}

/** Strip the final extension from a file name for display purposes */
export function baseName(name) {
  if (typeof name !== "string") return "";
  const idx = name.lastIndexOf(".");
  return idx > 0 ? name.slice(0, idx) : name;
}
