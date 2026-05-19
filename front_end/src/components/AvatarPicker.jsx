import { useEffect, useRef, useState } from "react";
import { BACKEND_URL } from "../config";
import "./AvatarPicker.css";

export default function AvatarPicker({ currentPath, onSelect, onClose }) {
  const [avatars, setAvatars] = useState([]);
  const [loading, setLoading] = useState(true);
  const overlayRef = useRef(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/avatars`)
      .then((r) => r.json())
      .then((data) => setAvatars(data.avatars || []))
      .finally(() => setLoading(false));
  }, []);

  function handleOverlayClick(e) {
    if (e.target === overlayRef.current) onClose();
  }

  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose(); }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="avatar-overlay" ref={overlayRef} onClick={handleOverlayClick}>
      <div className="avatar-modal">
        <div className="avatar-modal-header">
          <span className="avatar-modal-title">Choose Avatar</span>
          <button className="avatar-modal-close" onClick={onClose}>✕</button>
        </div>

        {loading ? (
          <p className="avatar-loading">Loading…</p>
        ) : (
          <div className="avatar-grid">
            {avatars.map((path) => (
              <button
                key={path}
                className={`avatar-option ${path === currentPath ? "selected" : ""}`}
                onClick={() => { onSelect(path); onClose(); }}
              >
                <img
                  src={`${BACKEND_URL}/${path}`}
                  alt=""
                  loading="lazy"
                  draggable={false}
                />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
