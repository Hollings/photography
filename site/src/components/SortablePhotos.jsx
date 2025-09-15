import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, useSortable, arrayMove, rectSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { viaCee } from "../utils";

function SortableCard({ item, onSaveTitle, onDelete, onPublish, onUnpublish }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    border: "1px solid #ddd",
    padding: "0.5rem",
    background: isDragging ? "#eef5ff" : "white",
    cursor: "default",
  };

  return (
    <div ref={setNodeRef} style={style}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
        <button
          {...listeners}
          {...attributes}
          aria-label="Drag to reorder"
          title="Drag to reorder"
          style={{ cursor: "grab", border: 0, background: "transparent", padding: 4, marginRight: 6 }}
        >
          ☰
        </button>
        <div style={{ flex: 1, height: 1, borderBottom: "1px dashed #ddd" }} />
      </div>
      <img
        src={viaCee(item.thumbnail_url || item.small_url || item.original_url)}
        alt={item.title || item.name}
        style={{ width: "100%", aspectRatio: "1/1", objectFit: "cover", display: "block" }}
      />
      <div style={{ marginTop: "0.5rem", fontSize: ".85rem", lineHeight: 1.3 }}>
        <label style={{ display: "block", marginBottom: 8 }}>
          <span style={{ display: "block", color: "#777", marginBottom: 4 }}>Title (display)</span>
          <input
            value={item._title ?? item.title ?? ""}
            onChange={e => onSaveTitle(item.id, e.target.value, false)}
            onKeyDown={e => { if (e.key === 'Enter') onSaveTitle(item.id, e.target.value, true); }}
            style={{ width: "100%" }}
            placeholder="Optional display title"
          />
        </label>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={() => onSaveTitle(item.id, item._title ?? item.title ?? "", true)} style={{ flex: "0 0 auto" }}>Save</button>
          <div style={{ flex: 1 }} />
          <button onClick={() => onDelete(item.id)} style={{ flex: "0 0 auto" }}>Delete</button>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
          <span style={{ color: "#666" }}>
            {item.posted_at ? `Published ${new Date(item.posted_at).toLocaleString()}` : 'Not published'}
          </span>
          <div style={{ flex: 1 }} />
          {item.posted_at ? (
            <button onClick={() => onUnpublish(item.id)}>Unpublish</button>
          ) : (
            <button onClick={() => onPublish(item.id)}>Publish</button>
          )}
        </div>
      </div>
    </div>
  );
}

SortableCard.propTypes = {
  item: PropTypes.object.isRequired,
  onSaveTitle: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onPublish: PropTypes.func.isRequired,
  onUnpublish: PropTypes.func.isRequired,
};

export default function SortablePhotos({ items, setItems, persistOrder, onDelete, onSaveTitle, onPublish, onUnpublish }) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));
  const ids = useMemo(() => items.map(i => i.id), [items]);
  const [activeId, setActiveId] = useState(null);

  const handleDragEnd = ({ active, over }) => {
    setActiveId(null);
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex(i => i.id === active.id);
    const newIndex = items.findIndex(i => i.id === over.id);
    if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex) return;
    const next = arrayMove(items, oldIndex, newIndex);
    setItems(next);
    persistOrder(next);
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={({ active }) => setActiveId(active?.id ?? null)}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveId(null)}
    >
      <SortableContext items={ids} strategy={rectSortingStrategy}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: "1rem",
        }}>
          {items.map(item => (
            <SortableCard key={item.id} item={item} onSaveTitle={onSaveTitle} onDelete={onDelete} onPublish={onPublish} onUnpublish={onUnpublish} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}

SortablePhotos.propTypes = {
  items: PropTypes.array.isRequired,
  setItems: PropTypes.func.isRequired,
  persistOrder: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onSaveTitle: PropTypes.func.isRequired,
  onPublish: PropTypes.func.isRequired,
  onUnpublish: PropTypes.func.isRequired,
};
