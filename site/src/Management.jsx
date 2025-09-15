import React, { useEffect, useState, useCallback } from "react";
import { viaCee } from "./utils";

export default function Management() {
  const [photos, setPhotos] = useState([]);
  const [title, setTitle]   = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [dragIdx,    setDragIdx]    = useState(null);

  /* ----------------------------- helpers -------------------------------- */
  const refresh = useCallback(() => {
    fetch("/photos")
      .then(r => r.json())
      .then(setPhotos)
      .catch(console.error);
  }, []);

  const deletePhoto = id => {
    if (!confirm("Delete this photo?")) return;
    fetch(`/photos/${id}`, { method: "DELETE" })
      .then(() => setPhotos(p => p.filter(ph => ph.id !== id)))
      .catch(console.error);
  };

  const saveName = (p) => {
    const name = (p._name ?? p.name).trim();
    if (!name || name === p.name) return;
    fetch(`/photos/${p.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    })
      .then(r => {
        if (!r.ok) throw new Error(`Rename failed: ${r.status}`);
        return r.json();
      })
      .then(updated => {
        setPhotos(prev => prev.map(x => x.id === p.id ? updated : x));
      })
      .catch(err => alert(err.message));
  };

  const uploadFiles = files => {
    Array.from(files).forEach(file => {
      const fd = new FormData();
      fd.append("file", file);
      if (title) fd.append("title", title);
      fetch("/photos", { method: "POST", body: fd })
        .then(refresh)
        .catch(console.error);
    });
  };

  const persistOrder = order => {
    order.forEach((p, idx) => {
      if (p.sort_order !== idx) {
        fetch(`/photos/${p.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sort_order: idx })
        }).catch(console.error);
        p.sort_order = idx;   // optimistic update
      }
    });
  };

  /* ------------------------- bulk drag‑and‑drop ------------------------- */
  const handleDrag = e => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = e => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.length) uploadFiles(e.dataTransfer.files);
  };

  const handleInputChange = e => {
    if (e.target.files?.length) uploadFiles(e.target.files);
    e.target.value = "";
  };

  /* -------------------- per‑photo drag‑to‑reorder ----------------------- */
  const handleDragStartItem = idx => () => setDragIdx(idx);

  const handleDragOverItem = idx => e => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === idx) return;
    setPhotos(prev => {
      const arr = [...prev];
      const [moved] = arr.splice(dragIdx, 1);
      arr.splice(idx, 0, moved);
      return arr;
    });
    setDragIdx(idx);
  };

  const handleDragEndItem = () => {
    setDragIdx(null);
    setPhotos(curr => {
      persistOrder(curr);
      return curr;
    });
  };

  /* ------------------------------ initial load -------------------------- */
  useEffect(refresh, [refresh]);

  /* ------------------------------ render -------------------------------- */
  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1>Photo Management</h1>

      {/* ---------- upload zone ------------------------------------------ */}
      <section
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        style={{
          border: "2px dashed #aaa",
          borderRadius: 8,
          padding: "2rem",
          textAlign: "center",
          background: dragActive ? "#f6f8fa" : "transparent",
          marginBottom: "2rem",
          cursor: "pointer"
        }}
        onClick={() => document.getElementById("file-picker").click()}
      >
        <p style={{ margin: 0, fontSize: "1.1rem" }}>
          Drag &amp; drop images here — or click to choose multiple
        </p>
        <input
          id="file-picker"
          type="file"
          accept="image/*"
          multiple
          onChange={handleInputChange}
          style={{ display: "none" }}
        />
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap", justifyContent: "center" }}>
          <input
            type="text"
            placeholder="Optional title (applied to each)"
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
        </div>
      </section>

      {/* ---------- list -------------------------------------------------- */}
      <h2>Existing Photos ({photos.length})</h2>
      <p style={{ fontSize: ".85rem", marginTop: 0 }}>Tip: drag thumbnails to reorder</p>
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
        gap: "1rem"
      }}>
        {photos.map((p, i) => (
          <div
            key={p.id}
            draggable
            onDragStart={handleDragStartItem(i)}
            onDragOver={handleDragOverItem(i)}
            onDragEnd={handleDragEndItem}
            style={{
              border: "1px solid #ddd",
              padding: "0.5rem",
              background: dragIdx === i ? "#f0f6ff" : "white",
              cursor: "grab"
            }}
          >
            <img
              src={viaCee(p.thumbnail_url || p.small_url || p.original_url)}
              alt={p.title || p.name}
              style={{ width: "100%", aspectRatio: "1/1", objectFit: "cover" }}
            />
            <div style={{ marginTop: "0.5rem", fontSize: ".85rem", lineHeight: 1.3 }}>
              <label style={{ display: "block", marginBottom: 4 }}>
                <span style={{ display: "block", color: "#777", marginBottom: 4 }}>File name</span>
                <input
                  value={p._name ?? p.name}
                  onChange={e => setPhotos(prev => prev.map(x => x.id === p.id ? { ...x, _name: e.target.value } : x))}
                  onKeyDown={e => { if (e.key === 'Enter') saveName(p); }}
                  style={{ width: "100%" }}
                />
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => saveName(p)} style={{ flex: "0 0 auto" }}>Save</button>
                <button onClick={() => setPhotos(prev => prev.map(x => x.id === p.id ? { ...x, _name: undefined } : x))} style={{ flex: "0 0 auto" }}>Reset</button>
                <div style={{ flex: 1 }} />
                <button onClick={() => deletePhoto(p.id)} style={{ flex: "0 0 auto" }}>Delete</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
