import { motion } from "framer-motion";

/**
 * Scintilla — mascotte inline (SVG) creata specificamente per la pagina
 * "Sessualità e Disabilità". Rappresenta la scintilla di desiderio, curiosità
 * e vita che rimane accesa oltre ogni cambiamento del corpo o della vita.
 *
 * Design principles:
 * - Astratta, mai riferimenti diretti a disabilità (nessuna rappresentazione
 *   fisica di limitazioni o ausili)
 * - Coerente con lo stile dei mascot esistenti (forme arrotondate, tratti
 *   morbidi, linee nere sottili)
 * - Palette del brand: corpo terracotta / crema, scintilla oro
 */
export default function Scintilla({ size = 240, className = "", animation = "breathe" }) {
  const anim = animation === "breathe"
    ? { animate: { scale: [1, 1.03, 1] }, transition: { duration: 3.6, repeat: Infinity, ease: "easeInOut" } }
    : animation === "float"
    ? { animate: { y: [0, -6, 0] }, transition: { duration: 4, repeat: Infinity, ease: "easeInOut" } }
    : {};
  const sparkAnim = { animate: { scale: [1, 1.2, 1], opacity: [0.9, 1, 0.9] },
    transition: { duration: 2.2, repeat: Infinity, ease: "easeInOut" } };

  return (
    <motion.div
      {...anim}
      data-testid="mascot-scintilla"
      className={`inline-block select-none pointer-events-none ${className}`}
      style={{ width: size, height: "auto" }}
    >
      <svg viewBox="0 0 240 260" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "auto" }}>
        {/* Warm glow behind the body */}
        <ellipse cx="120" cy="145" rx="105" ry="98" fill="url(#glow)" opacity="0.35" />

        {/* Body — rounded blob, warm terracotta */}
        <path
          d="M120 40 C170 40 205 78 205 130 C205 178 172 220 120 220 C68 220 35 178 35 130 C35 78 70 40 120 40 Z"
          fill="#E07A3C"
          stroke="#1C1C1C" strokeWidth="4" strokeLinejoin="round"
        />

        {/* Eyes — closed, gentle */}
        <path d="M85 118 Q92 125 100 118" stroke="#1C1C1C" strokeWidth="3.5" strokeLinecap="round" fill="none" />
        <path d="M140 118 Q147 125 155 118" stroke="#1C1C1C" strokeWidth="3.5" strokeLinecap="round" fill="none" />

        {/* Serene mouth — soft smile */}
        <path d="M108 155 Q120 168 132 155" stroke="#1C1C1C" strokeWidth="3.5" strokeLinecap="round" fill="none" />

        {/* Blush cheeks */}
        <ellipse cx="72" cy="150" rx="9" ry="6" fill="#F5A97F" opacity="0.85" />
        <ellipse cx="168" cy="150" rx="9" ry="6" fill="#F5A97F" opacity="0.85" />

        {/* The Scintilla (spark) — a small warm light held above/beside the body */}
        <motion.g {...sparkAnim} style={{ transformOrigin: "180px 60px" }}>
          {/* Star-like spark */}
          <path
            d="M180 40 L184 56 L200 60 L184 64 L180 80 L176 64 L160 60 L176 56 Z"
            fill="#F5D419"
            stroke="#1C1C1C" strokeWidth="2.5" strokeLinejoin="round"
          />
          {/* Inner highlight */}
          <circle cx="180" cy="60" r="3" fill="#FFFFFF" opacity="0.9" />
        </motion.g>

        {/* Small orbit dots — subtle sparkles */}
        <circle cx="205" cy="90" r="3" fill="#F5D419" stroke="#1C1C1C" strokeWidth="1.5" />
        <circle cx="155" cy="35" r="2.5" fill="#F5D419" stroke="#1C1C1C" strokeWidth="1.2" />

        <defs>
          <radialGradient id="glow" cx="0.5" cy="0.35" r="0.75">
            <stop offset="0%" stopColor="#F5D419" stopOpacity="0.7" />
            <stop offset="70%" stopColor="#F5D419" stopOpacity="0" />
          </radialGradient>
        </defs>
      </svg>
    </motion.div>
  );
}
