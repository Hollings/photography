import React from "react";
import Photo from "./Photo";

export default function Gallery({ items }) {
  return (
    <div id="gallery" className="gallery">
      {items.map(p => <Photo key={p.sha1 || p.url} photo={p} />)}
    </div>
  );
}
