import React from "react";
import PropTypes from "prop-types";
import { extractAperture, formatShutter, viaCee, baseName } from "../utils";

export default function Photo({ photo, size = "small", layout = "grid" }) {
  console.log("PHOTO")
  const {
    name,
    original_url,
    small_url,
    thumbnail_url,
    title,
    camera,
    lens,
    iso,
    shutter_speed,
    focal_length,
    created_at,
  } = photo;

// Build responsive sources
const full = viaCee(original_url);
const thumb = thumbnail_url ? viaCee(thumbnail_url) : null;
const small = small_url ? viaCee(small_url) : null;
const medium = photo.medium_url ? viaCee(photo.medium_url) : null;

// Fallback src (small → thumbnail → full)
const src = small || thumb || full;

// srcset only includes sizes we know exist to avoid 404s
const srcSet = [
  thumb && `${thumb} 400w`,
  small && `${small} 1600w`,
  medium && `${medium} 2560w`,
].filter(Boolean).join(", ");

// sizes hint: single column uses full viewport width; grid uses fractions
const sizes = layout === "single"
  ? "100vw"
  : "(max-width: 600px) 100vw, (max-width: 1200px) 50vw, 33vw";


  // derived metadata
  const formattedShutter  = formatShutter(shutter_speed);
  const formattedAperture = (photo.aperture ? photo.aperture.replace(/^f\//i, "") : extractAperture(lens || ""));
  const when = photo.taken_at || created_at;
  const taken =
    when
      ? new Date(when).toLocaleDateString(undefined, {
          month: "long",
          year:  "numeric",
        })
      : "—";
  console.log(src)
  return (
    <figure className="photo-card">
      <a href={full} target="_blank" rel="noopener noreferrer">
        <img
          src={src}
          srcSet={srcSet || undefined}
          sizes={srcSet ? sizes : undefined}
          alt={title ?? name}
          loading="lazy"
        />
      </a>

      {/* centred, grey caption */}
      <figcaption className="caption">
        <span className="title">{title ?? baseName(name) ?? "—"}</span>
        <span className="meta">
          {camera && `${camera} ${lens ?? ""}`}<br/>
          {formattedAperture && `f/${formattedAperture}`}
          {focal_length && ` • ${focal_length}`}
          {iso && ` • ISO ${iso}`}
          {formattedShutter && ` • ${formattedShutter}`}
        </span>
        <br />
        <span className="date">{taken}</span>
      </figcaption>
    </figure>
  );
}

Photo.propTypes = {
  photo: PropTypes.shape({
    id:            PropTypes.number.isRequired,
    name:          PropTypes.string.isRequired,
    original_url:  PropTypes.string.isRequired,
    medium_url:    PropTypes.string,
    small_url:     PropTypes.string,      // no longer “isRequired”
    thumbnail_url: PropTypes.string.isRequired,
    sort_order:    PropTypes.number,
    title:         PropTypes.string,
    camera:        PropTypes.string,
    lens:          PropTypes.string,
    iso:           PropTypes.number,
    aperture:      PropTypes.string,
    shutter_speed: PropTypes.string,
    focal_length:  PropTypes.string,
    created_at:    PropTypes.string,
  }).isRequired,
  size: PropTypes.oneOf(["thumbnail", "small", "full"]),
  layout: PropTypes.oneOf(["grid", "single"]),
};
