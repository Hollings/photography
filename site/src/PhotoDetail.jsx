import React, { useEffect, useState } from "react";
import { viaCee, extractAperture, formatShutter, baseName } from "./utils";

export default function PhotoDetail() {
  const id = window.location.pathname.split("/")[2];
  const [photo, setPhoto] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    fetch(`/photos/${id}`)
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(setPhoto)
      .catch(e => setErr(e.message));
  }, [id]);

  if (err) return <main style={{ maxWidth: 960, margin: "0 auto", padding: "1rem" }}><p>Error: {err}</p></main>;
  if (!photo) return <main style={{ maxWidth: 960, margin: "0 auto", padding: "1rem" }}><p>Loading…</p></main>;

  const full   = viaCee(photo.original_url);
  const medium = photo.medium_url ? viaCee(photo.medium_url) : null;
  const small  = photo.small_url ? viaCee(photo.small_url) : null;
  const src    = medium || small || full;

  const when   = photo.taken_at || photo.created_at;
  const taken  = when ? new Date(when).toLocaleString(undefined, { dateStyle: "long" }) : "—";
  const shutter = formatShutter(photo.shutter_speed);
  const aperture = extractAperture(photo.lens || "");

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "1rem" }}>
      <p><a href="/">← Back to gallery</a></p>
      <article>
        <h1 style={{ marginTop: 0 }}>{photo.title || baseName(photo.name)}</h1>
        <a href={full} target="_blank" rel="noopener noreferrer">
          <img src={src} alt={photo.title || photo.name} style={{ width: "100%", height: "auto", display: "block", borderRadius: 8 }} />
        </a>
        <section style={{ marginTop: "1rem", color: "#555" }}>
          <div><strong>Taken:</strong> {taken}</div>
          {photo.camera && (<div><strong>Camera:</strong> {photo.camera}</div>)}
          {photo.lens && (<div><strong>Lens:</strong> {photo.lens}</div>)}
          <div>
            {aperture && (<span>f/{aperture}</span>)}
            {photo.focal_length && (<span> • {photo.focal_length}</span>)}
            {photo.iso && (<span> • ISO {photo.iso}</span>)}
            {shutter && (<span> • {shutter}</span>)}
          </div>
          <div style={{ marginTop: 8 }}>
            <a href={full} target="_blank" rel="noopener noreferrer">Open original</a>
          </div>
        </section>
      </article>
    </main>
  );
}
