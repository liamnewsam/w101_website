import { pipSrc } from "../config";
import "./PipGrid.css";


export default function PipGrid({pips, pipIconSize}) {
    const pip_icons = Object.entries(pips).flatMap(
        ([key, count]) => Array(Math.max(0, Math.floor(count || 0))).fill({ src: pipSrc(key), key })
    );

    return (
        <div className="pip-grid">
            {pip_icons.map(({ src, key }, index) => (
                <img
                    src={src}
                    alt={key}
                    className="pip-icon"
                    style={{ height: pipIconSize, width: pipIconSize }}
                    key={index}
                />
            ))}
        </div>
    )
}