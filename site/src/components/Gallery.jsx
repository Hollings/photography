import React from "react";
import Photo from "./Photo";

export default function Gallery({ items, layout = "grid" }) {
  const cls = `gallery layout-${layout}`;
  return (
    <div id="gallery" className={cls}>
      {items.map(p => <Photo key={p.sha1 || p.url} photo={p} layout={layout} />)}
    </div>
  );
}
