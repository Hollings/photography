import React, { useEffect, useRef, useState, useCallback } from "react";
import Gallery from "./components/Gallery";
import "./index.css";

const BATCH = 10;

export default function App() {
  const [all,  setAll]  = useState([]);
  const [show, setShow] = useState([]);
  const next   = useRef(0);
  const sent   = useRef(null);

  // Fetch & sort photos
  useEffect(() => {
    fetch("/photos.json")
      .then(r => r.json())
      .then(d => {
        const arr = Array.isArray(d) ? d : Object.values(d);
        arr.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
        setAll(arr);
      })
      .catch(console.error);
  }, []);

  // Load helper
  const load = useCallback(() => {
    if (next.current >= all.length) return;         // nothing left
    setShow(v => {
      const slice = all.slice(next.current, next.current + BATCH);
      next.current += slice.length;
      return [...v, ...slice];
    });
  }, [all]);

  // Infinite scroll
  useEffect(() => {
    if (!all.length) return;
    load();                                         // first batch

    const ob = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          load();
          if (next.current >= all.length && sent.current) {
            ob.disconnect();                       // stop once done
          }
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
