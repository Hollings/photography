import React from "react";
import PropTypes from "prop-types";
import { extractAperture, formatShutter } from "../utils";

export default function Photo({ photo, size = "small" }) {
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

  // pick the correct image size
  const src =
    size === "full"
      ? original_url
      : size === "thumbnail"
      ? thumbnail_url
      : small_url;

  // derived metadata
  const formattedShutter  = formatShutter(shutter_speed);
  const formattedAperture = extractAperture(lens || "");
  const taken =
    created_at
      ? new Date(created_at).toLocaleDateString(undefined, {
          month: "long",
          year:  "numeric",
        })
      : "—";

  return (
    <figure className="photo-card">
      <img
        src={src}
        alt={title ?? name}
        loading="lazy"
        width="100%"
        height="auto"
      />

      {/* centred, grey caption */}
      <figcaption className="caption">
        <span className="title">{title ?? name}</span>
        <br />
        <span className="meta">
          {camera && `${camera} ${lens ?? ""}`}
          {formattedAperture && ` • f/${formattedAperture}`}
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
    small_url:     PropTypes.string.isRequired,
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
};
