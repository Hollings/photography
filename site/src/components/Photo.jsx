import React from "react";
import { formatShutter, extractAperture } from "../utils";

export default function Photo({ photo }) {
  const {
    title, name, camera, lens, shutter_speed,
    iso, rating, url, small_url, thumbnail_url,
  } = photo;

  const src      = small_url || thumbnail_url || url;
  const shutter  = formatShutter(shutter_speed);
  const aperture = extractAperture(lens);
  const exposure = [shutter, aperture && `f/${aperture}`, iso && `ISO ${iso}`]
                     .filter(Boolean).join(" | ");

  return (
    <div className="photo">
      <a href={url} target="_blank" rel="noopener noreferrer">
        <img
          src={src}
          alt={title || name || "Photo"}
          loading="lazy"
          decoding="async"
        />
      </a>
      <div className="caption">
        <span className="title">{title || name}</span><br />
        <span className="meta">
          {camera}<br />
          {lens}<br />
          {exposure}{rating != null && ` | ★ ${rating}`}
        </span>
      </div>
    </div>
  );
}
