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
