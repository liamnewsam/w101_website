import { useState, useRef, useEffect } from "react";
import { BACKEND_URL, BATTLE_PATH, SCHOOLS, pipSrc} from "../config";
import "./SchoolPipSelector.css";

export default function SchoolPipSelector({ currentSchool, size, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  return (
    <div ref={ref} className="school-pip-selector">
      <div
        className="school-pip-current"
        style={{ width: size, height: size }}
        onClick={() => setOpen(o => !o)}
      >
        <img src={pipSrc(currentSchool)} alt={currentSchool} style={{ width: size, height: size }} />
      </div>

      {open && (
        <div className="school-pip-menu">
          {SCHOOLS.map(school => (
            <img
              key={school}
              src={pipSrc(school)}
              alt={school}
              className={`school-pip-option${school === currentSchool ? " selected" : ""}`}
              style={{ width: size, height: size }}
              onClick={() => { onChange(school); setOpen(false); }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
