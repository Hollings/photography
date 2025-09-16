import React, { useEffect, useRef, useState, useCallback } from "react";
import Gallery from "./components/Gallery";
import "./index.css";

const BATCH = 10;

export default function App() {
  const [all,  setAll]  = useState([]);
  const [show, setShow] = useState([]);
  const [layout, setLayout] = useState(() => localStorage.getItem("cee_layout") || "single");
  const next   = useRef(0);
  const sent   = useRef(null);

  // 1 – Fetch once and load the first batch immediately
  useEffect(() => {
    fetch("/photos")
      .then(r => r.json())
      .then(raw => {
        const arr    = Array.isArray(raw) ? raw : Object.values(raw);
        const sorted = [...arr].sort((a, b) => a.sort_order - b.sort_order);
        const mapped = sorted.map(p => ({ ...p, url: p.original_url }));
        setAll(mapped);

        const first  = mapped.slice(0, BATCH);   // prime the gallery
        setShow(first);
        next.current = first.length;
      })
      .catch(console.error);
  }, []);

  // 2 – Function that pushes the next batch
  const loadMore = useCallback(() => {
    if (next.current >= all.length) return;
    setShow(prev => {
      const slice = all.slice(next.current, next.current + BATCH);
      next.current += slice.length;
      return [...prev, ...slice];
    });
  }, [all]);

  // 3 – Infinite scroll once data AND sentinel are in place
  useEffect(() => {
    if (!all.length || !sent.current) return;

    const ob = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && loadMore(),
      { rootMargin: "200px" }
    );

    ob.observe(sent.current);
    return () => ob.disconnect();
  }, [all, loadMore]);

  return (
    <>
      <div className="toolbar">
        <a className="subscribe" href="/feed.xml" target="_blank" rel="noopener noreferrer">Subscribe</a>
        <div className="toggle" role="tablist" aria-label="View layout">
          <button
            className={layout === "grid" ? "active" : ""}
            onClick={() => { setLayout("grid"); localStorage.setItem("cee_layout", "grid"); }}
            role="tab" aria-selected={layout === "grid"}
          >Grid</button>
          <button
            className={layout === "single" ? "active" : ""}
            onClick={() => { setLayout("single"); localStorage.setItem("cee_layout", "single"); }}
            role="tab" aria-selected={layout === "single"}
          >Single</button>
        </div>
      </div>

      <Gallery items={show} layout={layout} />
      <div ref={sent} style={{ height: 1 }} />
    </>
  );
}
