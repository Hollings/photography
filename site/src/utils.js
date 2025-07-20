// Format shutter speeds supplied as numbers *or* fractions, e.g. "1/250"

/**
 * Compute a SHA‑1 hex digest in **both** browsers and Node.
 * @param {string|Uint8Array} input
 * @returns {Promise<string>} 40‑char hex string
 */
export async function sha1Hex(input) {
  const data = typeof input === 'string' ? new TextEncoder().encode(input) : input;

  if (globalThis.crypto?.subtle?.digest) {
    const buf = await crypto.subtle.digest('SHA-1', data);
    return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  // Node path — built‑in ‘crypto’ module
  const { createHash } = await import('crypto');
  return createHash('sha1').update(data).digest('hex');
}

export function formatShutter(s) {
  if (s == null) return "";

  let v;

  if (typeof s === "number") {
    v = s;
  } else {
    const str = String(s).trim();
    if (str.includes("/")) {
      const [num, den] = str.split("/").map(Number);
      if (num && den) v = num / den;
    } else {
      v = parseFloat(str);
    }
  }

  if (!v) return "";
  return v >= 1 ? `${v}s` : `1/${Math.round(1 / v)}s`;
}

// Extract aperture from "f/2.8", "F2.8", etc.
export function extractAperture(lens = "") {
  const m = lens.match(/f\/?(\d+(\.\d+)?)/i);
  return m ? m[1] : "";
}
