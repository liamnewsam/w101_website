import { useState } from "react";
import { BACKEND_URL, BATTLE_PATH} from "../config";
import "./PipGrid.css";

const pip_map = {
    "regular": "pips/Pip.png",
    "powerpip": "pips/Power_Pip.png"
}

export default function PipGrid({pips, pipIconSize}) {
    const pip_icons = Object.entries(pips).flatMap(
        ([key, count]) => Array(count).fill(pip_map[key])
    );

    return (
        <div className="pip-grid">
            {pip_icons.map((icon, index) => (
                <img 
                    src={BACKEND_URL+BATTLE_PATH+icon}
                    alt={icon}
                    className="pip-icon"
                    style={{ height: pipIconSize, width: pipIconSize }}
                    key={index}
                />
            ))}
        </div>
    )
}