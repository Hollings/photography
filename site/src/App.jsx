import React, { useEffect, useRef, useState, useCallback } from "react";
import Gallery from "./components/Gallery";
import "./index.css";

const BATCH = 10;

export default function App() {
  const [all,  setAll]  = useState([]);
  const [show, setShow] = useState([]);
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
      <Gallery items={show} />
      <div ref={sent} style={{ height: 1 }} />
    </>
  );
}
