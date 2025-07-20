import React, { useEffect, useRef, useState, useCallback } from "react";
import Gallery from "./components/Gallery";
import "./index.css";

const BATCH = 10;

export default function App() {
  const [all,  setAll]  = useState([]);
  const [show, setShow] = useState([]);
  const next   = useRef(0);
  const sent   = useRef(null);

  // Fetch photos in the order provided by the API (sort_order → newest)
  useEffect(() => {
    fetch("/photos.json")
      .then(r => r.json())
      .then(d => setAll(Array.isArray(d) ? d : Object.values(d)))
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
