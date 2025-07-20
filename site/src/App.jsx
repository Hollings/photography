import React, { useEffect, useRef, useState, useCallback } from "react";
import Gallery from "./components/Gallery";
import "./index.css";

const BATCH = 10;

export default function App() {
  const [all,  setAll]  = useState([]);
  const [show, setShow] = useState([]);
  const next   = useRef(0);
  const sent   = useRef(null);

  // Fetch photos from API instead of JSON file
  useEffect(() => {
    fetch("/photos")
      .then(r => r.json())
      .then(data => {
        const arr = Array.isArray(data) ? data : Object.values(data);
        // sort by sort_order ascending
        const sorted = arr.sort((a, b) => a.sort_order - b.sort_order);
        // map original_url to url for the Photo component
        const mapped = sorted.map(p => ({ ...p, url: p.original_url }));
        setAll(mapped);
      })
      .catch(console.error);
  }, []);

  const load = useCallback(() => {
    if (next.current >= all.length) return;
    setShow(v => {
      const slice = all.slice(next.current, next.current + BATCH);
      next.current += slice.length;
      return [...v, ...slice];
    });
  }, [all]);

  useEffect(() => {
    if (!all.length) return;
    load();

    const ob = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          load();
          if (next.current >= all.length && sent.current) ob.disconnect();
        }
      },
      { rootMargin: "200px" }
    );

    if (sent.current) ob.observe(sent.current);
    return () => ob.disconnect();
  }, [all, load]);

  return (
    <>
      <h1>Photo Gallery</h1>
      <Gallery items={show} />
      <div id="sentinel" ref={sent} style={{ height: 1 }} />
    </>
  );
}
