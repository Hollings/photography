import React, { useEffect, useState, useCallback } from "react";
import { viaCee } from "./utils";
import SortablePhotos from "./components/SortablePhotos";

export default function Management() {
  const [photos, setPhotos] = useState([]);
  const [title, setTitle]   = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [uploads,    setUploads]    = useState([]); // [{id,name,progress,status,error}]
  const UPLOAD_CONCURRENCY = 3; // set to 1 for strict sequential

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

  const saveEdits = (p) => {
    const nextTitle = (p._title ?? p.title ?? "").trim();
    if (nextTitle === (p.title ?? "")) return;
    fetch(`/photos/${p.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: nextTitle })
    })
      .then(r => {
        if (!r.ok) throw new Error(`Update failed: ${r.status}`);
        return r.json();
      })
      .then(updated => {
        setPhotos(prev => prev.map(x => x.id === p.id ? updated : x));
      })
      .catch(err => alert(err.message));
  };

  const uploadFiles = files => {
    const list = Array.from(files);
    // Build a set of existing names to skip duplicates (client-side fast path)
    const existing = new Set(photos.map(p => p.name));
    const toUpload = [];
    list.forEach((file, idx) => {
      if (existing.has(file.name)) {
        const id = `${Date.now()}-skip-${idx}-${Math.random().toString(36).slice(2,6)}`;
        setUploads(u => [...u, { id, name: file.name, progress: 0, status: "skipped", error: null }]);
      } else {
        existing.add(file.name);
        toUpload.push(file);
      }
    });

    if (toUpload.length === 0) {
      setTimeout(() => setUploads([]), 1000);
      return Promise.resolve();
    }

    // bounded concurrency queue
    let i = 0, inFlight = 0, done = 0;
    return new Promise(resolve => {
      const pump = () => {
        while (inFlight < UPLOAD_CONCURRENCY && i < toUpload.length) {
          const file = toUpload[i++];
          inFlight++;
          uploadOne(file, i-1)
            .catch(() => {})
            .finally(() => {
              inFlight--; done++;
              if (done === toUpload.length) {
                // clear panel shortly after finishing
                setTimeout(() => setUploads([]), 1000);
                resolve();
              } else {
                pump();
              }
            });
        }
      };
      pump();
    });
  };

  const uploadOne = (file, idx) => new Promise((resolve) => {
    const id = `${Date.now()}-${idx}-${Math.random().toString(36).slice(2,8)}`;
    const rec = { id, name: file.name, progress: 0, status: "uploading", error: null };
    setUploads(u => [...u, rec]);

    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/photos");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        setUploads(u => u.map(x => x.id === id ? { ...x, progress: pct } : x));
      }
    };
    xhr.upload.onload = () => {
      setUploads(u => u.map(x => x.id === id ? { ...x, status: "processing", progress: 100 } : x));
    };
    xhr.onerror = () => {
      setUploads(u => u.map(x => x.id === id ? { ...x, status: "error", error: "Network error" } : x));
      resolve();
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        setUploads(u => u.map(x => x.id === id ? { ...x, status: "done" } : x));
        refresh();
      } else if (xhr.status === 409) {
        // server-side duplicate safeguard
        setUploads(u => u.map(x => x.id === id ? { ...x, status: "skipped", error: null } : x));
      } else {
        setUploads(u => u.map(x => x.id === id ? { ...x, status: "error", error: `HTTP ${xhr.status}` } : x));
      }
      resolve();
    };
    xhr.send(fd);
  });

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

  // DnD handled by SortablePhotos component

  /* ------------------------------ initial load -------------------------- */
  useEffect(refresh, [refresh]);

  /* ------------------------------ render -------------------------------- */
  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1>Photo Management</h1>

      {/* ---------- uploads panel --------------------------------------- */}
      {uploads.length > 0 && (
        <section style={{
          background: "#fff",
          border: "1px solid #eee",
          borderRadius: 8,
          padding: "1rem",
          marginBottom: "1.5rem",
          boxShadow: "0 1px 2px rgba(0,0,0,.04)"
        }}>
          <div style={{ marginBottom: 8, fontWeight: 600 }}>
            Active {uploads.filter(u => u.status === 'uploading' || u.status === 'processing').length} / {uploads.length}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {uploads.map(u => (
              <div key={u.id} style={{ fontSize: ".9rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>{u.name}</span>
                  <span style={{ color: "#666" }}>
                    {u.status === 'uploading' && `${u.progress}%`}
                    {u.status === 'processing' && 'processing…'}
                    {u.status === 'done' && 'done'}
                    {u.status === 'error' && (u.error || 'error')}
                  </span>
                </div>
                <div style={{ height: 6, background: "#f1f1f1", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{ width: `${u.progress}%`, height: "100%", background: u.status === 'error' ? '#e57373' : '#4caf50', transition: 'width .2s' }} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

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
      <SortablePhotos
        items={photos}
        setItems={setPhotos}
        persistOrder={persistOrder}
        onDelete={deletePhoto}
        onSaveTitle={(id, value, commit) => {
          setPhotos(prev => prev.map(x => x.id === id ? { ...x, _title: value } : x));
          if (commit) {
            const p = photos.find(x => x.id === id);
            if (!p) return;
            const nextTitle = (value ?? "").trim();
            if (nextTitle === (p.title ?? "")) return;
            fetch(`/photos/${id}`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ title: nextTitle })
            })
              .then(r => r.ok ? r.json() : Promise.reject(new Error(`Update failed: ${r.status}`)))
              .then(updated => setPhotos(prev => prev.map(x => x.id === id ? updated : x)))
              .catch(err => alert(err.message));
          }
        }}
      />
    </main>
  );
}
