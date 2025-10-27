import React, { useEffect, useState } from "react";
import { Rnd } from "react-rnd";
import { Button } from "@/components/ui/button"; // if using shadcn/ui
import axios from "axios";

/**
 * OverlayEditor component
 * Allows users to:
 *  - Create and position text/image overlays on video
 *  - Save/update/delete overlay settings via backend API
 */
export default function OverlayEditor({ videoRef }) {
  const [overlays, setOverlays] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [formData, setFormData] = useState({
    type: "text",
    content: "Sample Text",
    position: { x: 50, y: 50 },
    size: { width: 150, height: 50 },
  });

  // Load existing overlays from backend
  useEffect(() => {
    fetchOverlays();
  }, []);

  const fetchOverlays = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:5000/api/overlays");
      setOverlays(res.data);
    } catch (err) {
      console.error("Error loading overlays:", err);
    }
  };

  const createOverlay = async () => {
    try {
      const res = await axios.post("http://127.0.0.1:5000/api/overlays", formData);
      setOverlays([...overlays, res.data]);
    } catch (err) {
      console.error("Error creating overlay:", err);
    }
  };

  const updateOverlay = async (id, updated) => {
    try {
      await axios.put(`http://127.0.0.1:5000/api/overlays/${id}`, updated);
      setOverlays(overlays.map(o => (o._id === id ? { ...o, ...updated } : o)));
    } catch (err) {
      console.error("Error updating overlay:", err);
    }
  };

  const deleteOverlay = async (id) => {
    try {
      await axios.delete(`http://127.0.0.1:5000/api/overlays/${id}`);
      setOverlays(overlays.filter(o => o._id !== id));
    } catch (err) {
      console.error("Error deleting overlay:", err);
    }
  };

  const handleDragStop = (id, d) => {
    const updated = { ...overlays.find(o => o._id === id) };
    updated.position = { x: d.x, y: d.y };
    updateOverlay(id, updated);
  };

  const handleResizeStop = (id, direction, ref, delta, position) => {
    const updated = { ...overlays.find(o => o._id === id) };
    updated.size = { width: ref.offsetWidth, height: ref.offsetHeight };
    updated.position = position;
    updateOverlay(id, updated);
  };

  return (
    <div className="relative w-full h-full">
      {/* Overlays on top of video */}
      {overlays.map((overlay) => (
        <Rnd
          key={overlay._id}
          size={{ width: overlay.size.width, height: overlay.size.height }}
          position={{ x: overlay.position.x, y: overlay.position.y }}
          bounds="parent"
          onDragStop={(e, d) => handleDragStop(overlay._id, d)}
          onResizeStop={(e, direction, ref, delta, position) =>
            handleResizeStop(overlay._id, direction, ref, delta, position)
          }
          style={{
            border: selectedId === overlay._id ? "2px solid #3b82f6" : "none",
            zIndex: 10,
          }}
          onClick={() => setSelectedId(overlay._id)}
        >
          {overlay.type === "text" ? (
            <div
              className="bg-black/40 text-white p-1 text-sm w-full h-full flex items-center justify-center rounded"
              style={{ fontSize: overlay.fontSize || 16 }}
            >
              {overlay.content}
            </div>
          ) : (
            <img
              src={overlay.content}
              alt="overlay"
              className="w-full h-full object-contain rounded"
            />
          )}
        </Rnd>
      ))}

      {/* Control panel */}
      <div className="absolute top-2 left-2 bg-white/90 p-3 rounded-lg shadow-md w-72 text-sm z-20">
        <h3 className="font-semibold mb-2 text-gray-700">Overlay Controls</h3>

        <label className="block text-gray-600 text-xs mb-1">Type</label>
        <select
          className="border rounded w-full mb-2 p-1"
          value={formData.type}
          onChange={(e) => setFormData({ ...formData, type: e.target.value })}
        >
          <option value="text">Text</option>
          <option value="image">Image</option>
        </select>

        <label className="block text-gray-600 text-xs mb-1">Content</label>
        <input
          type="text"
          className="border rounded w-full mb-2 p-1"
          placeholder="Text or image URL"
          value={formData.content}
          onChange={(e) => setFormData({ ...formData, content: e.target.value })}
        />

        <div className="flex gap-2">
          <Button size="sm" onClick={createOverlay}>Add</Button>
          {selectedId && (
            <Button
              size="sm"
              variant="destructive"
              onClick={() => deleteOverlay(selectedId)}
            >
              Delete
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
