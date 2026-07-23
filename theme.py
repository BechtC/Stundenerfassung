"""
Zentrales Theme-Modul: MagicBento-Look (Dark Theme, Tuerkis-Akzent).

Portierung der ReactBits-Komponente "MagicBento" (Border-Glow, Global
Spotlight, Tilt, Magnetism, Click-Ripple) nach Streamlit — ohne React,
ohne GSAP, ohne CDN. CSS wird global injiziert, das Maus-Tracking laeuft
in EINEM unsichtbaren components.html-iframe, das ueber
window.parent.document auf die Streamlit-Seite zugreift.
"""

import streamlit as st
import streamlit.components.v1 as components

# --- Farbpalette (Tuerkis-Akzent statt ReactBits-Lila) ---
GLOW_RGB = "42, 157, 143"        # #2A9D8F als r,g,b fuer rgba()
ACCENT = "#2A9D8F"               # Hauptakzent (Tuerkis)
ACCENT_LIGHT = "#5CC8BA"         # helle Abstufung
ACCENT_DIM = "#1F7A70"           # dunkle Abstufung
SECONDARY = "#457B9D"            # Sekundaerblau (bisherige Chart-Farbe)
CONTRAST = "#E63946"             # Kontrast/Signal (Timer-Rot)
BG_DARK = "#070b0e"              # Seitenhintergrund
BG_SIDEBAR = "#0b1114"           # Sidebar
CARD_BG = "#10151a"              # Bento-Karten
CARD_BORDER = "#1e2c30"          # Karten-Rand
TEXT = "#e6edf0"                 # Haupttext
TEXT_MUTED = "#8fa3ab"           # gedaempfter Text

# Chart-Palette fuer charts.py (Tuerkis-dominant, Blau sekundaer)
CHART_COLORS = [ACCENT, SECONDARY, ACCENT_LIGHT, CONTRAST, ACCENT_DIM]

# Effekt-Parameter (Originalwerte der ReactBits-Demo)
SPOTLIGHT_RADIUS = 750
TILT_DEG = 10          # max. Kipp-Winkel
MAGNETISM = 0.05       # Anziehungs-Faktor Richtung Maus


_CSS = f"""
<style>
    :root {{
        --glow-rgb: {GLOW_RGB};
        --glow-radius: 200px;
    }}

    .block-container {{ padding-top: 2rem; }}

    /* --- Sidebar --- */
    div[data-testid="stSidebar"] {{
        background: {BG_SIDEBAR};
        border-right: 1px solid {CARD_BORDER};
    }}

    /* --- Bento-Karten: Metrics + bordered Container --- */
    div[data-testid="stMetric"],
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        --glow-x: 50%;
        --glow-y: 50%;
        --glow-intensity: 0;
        position: relative;
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 20px;
        padding: 16px;
        transition: box-shadow 0.3s ease, border-color 0.3s ease;
        will-change: transform;
        overflow: visible;
    }}

    div[data-testid="stMetric"]:hover,
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
        box-shadow:
            0 8px 25px rgba(0, 0, 0, 0.5),
            0 0 30px rgba(var(--glow-rgb), 0.2);
    }}

    /* Border-Glow: radialer Verlauf am Rand, folgt der Maus.
       Mask-Trick aus MagicBento.css — nur der Rand (padding-Bereich
       der ::after-Box) bleibt sichtbar. */
    div[data-testid="stMetric"]::after,
    div[data-testid="stVerticalBlockBorderWrapper"]::after {{
        content: '';
        position: absolute;
        inset: 0;
        padding: 5px;
        background: radial-gradient(
            var(--glow-radius) circle at var(--glow-x) var(--glow-y),
            rgba(var(--glow-rgb), calc(var(--glow-intensity) * 0.8)) 0%,
            rgba(var(--glow-rgb), calc(var(--glow-intensity) * 0.4)) 30%,
            transparent 60%
        );
        border-radius: inherit;
        mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
        mask-composite: subtract;
        -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
        -webkit-mask-composite: xor;
        pointer-events: none;
        transition: opacity 0.3s ease;
        z-index: 1;
    }}

    /* Perspektive fuer den Tilt-Effekt */
    div[data-testid="stMainBlockContainer"],
    div[data-testid="stVerticalBlock"] {{
        perspective: 1000px;
    }}

    /* Metric-Innenleben lesbar halten */
    div[data-testid="stMetric"] label {{ color: {TEXT_MUTED} !important; }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{ color: {TEXT}; }}

    /* --- Buttons --- */
    div.stButton > button, div[data-testid="stSidebar"] button {{
        border-radius: 12px;
        transition: transform 0.15s ease, box-shadow 0.2s ease,
                    border-color 0.2s ease;
    }}
    div.stButton > button:hover, div[data-testid="stSidebar"] button:hover {{
        border-color: {ACCENT};
        box-shadow: 0 0 14px rgba(var(--glow-rgb), 0.35);
        transform: translateY(-1px);
    }}

    /* --- Click-Ripple --- */
    @keyframes bento-ripple {{
        from {{ transform: scale(0); opacity: 1; }}
        to   {{ transform: scale(1); opacity: 0; }}
    }}
    .bento-ripple {{
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(circle,
            rgba(var(--glow-rgb), 0.4) 0%,
            rgba(var(--glow-rgb), 0.2) 30%,
            transparent 70%);
        pointer-events: none;
        z-index: 2;
        animation: bento-ripple 0.8s ease-out forwards;
    }}

    /* --- Reduzierte Bewegung respektieren --- */
    @media (prefers-reduced-motion: reduce) {{
        div[data-testid="stMetric"],
        div[data-testid="stVerticalBlockBorderWrapper"],
        div.stButton > button {{
            transition: none !important;
        }}
        .bento-ripple {{ animation: none !important; }}
    }}
</style>
"""


def _effects_js() -> str:
    """JS fuer Spotlight, Border-Glow, Tilt, Magnetism und Ripple.

    Laeuft in einem unsichtbaren iframe und manipuliert
    window.parent.document. Idempotent: bei jedem Streamlit-Rerun wird
    der alte Zustand (Spotlight-Div, Listener, rAF-Loop) abgeraeumt.
    """
    return f"""
<script>
(function() {{
    const doc = window.parent.document;
    const win = window.parent;

    // Nur Desktop mit Maus, Bewegungsreduktion respektieren
    if (!win.matchMedia('(pointer: fine)').matches) return;
    if (win.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // --- Alten Zustand abraeumen (Streamlit fuehrt das iframe bei jedem
    //     Rerun neu aus) ---
    if (win.__bentoCleanup) {{ try {{ win.__bentoCleanup(); }} catch (e) {{}} }}

    const SPOTLIGHT_RADIUS = {SPOTLIGHT_RADIUS};
    const PROXIMITY = SPOTLIGHT_RADIUS * 0.5;
    const FADE_DISTANCE = SPOTLIGHT_RADIUS * 0.75;
    const TILT_DEG = {TILT_DEG};
    const MAGNETISM = {MAGNETISM};
    const GLOW_RGB = '{GLOW_RGB}';
    const CARD_SELECTOR =
        'div[data-testid="stMetric"], ' +
        'div[data-testid="stVerticalBlockBorderWrapper"]';

    // --- Spotlight-Div ---
    const spotlight = doc.createElement('div');
    spotlight.id = 'bento-spotlight';
    spotlight.style.cssText = `
        position: fixed;
        width: 800px; height: 800px;
        border-radius: 50%;
        pointer-events: none;
        background: radial-gradient(circle,
            rgba(${{GLOW_RGB}}, 0.15) 0%,
            rgba(${{GLOW_RGB}}, 0.08) 15%,
            rgba(${{GLOW_RGB}}, 0.04) 25%,
            rgba(${{GLOW_RGB}}, 0.02) 40%,
            rgba(${{GLOW_RGB}}, 0.01) 65%,
            transparent 70%);
        z-index: 200;
        opacity: 0;
        transform: translate(-50%, -50%);
        mix-blend-mode: screen;
    `;
    doc.body.appendChild(spotlight);

    // --- State ---
    let cards = [];
    let mouseX = -9999, mouseY = -9999;
    let spotX = -9999, spotY = -9999;      // gelerpte Spotlight-Position
    let spotOpacity = 0, spotTarget = 0;
    let mouseInside = false;
    let rafId = null;
    // pro Karte: aktuelle/gewuenschte Transform-Werte
    const cardState = new Map();

    function collectCards() {{
        cards = Array.from(doc.querySelectorAll(CARD_SELECTOR));
        for (const c of cards) {{
            if (!cardState.has(c)) {{
                cardState.set(c, {{ rx: 0, ry: 0, tx: 0, ty: 0 }});
            }}
        }}
    }}
    collectCards();

    // Streamlit rendert das DOM bei Reruns neu -> Karten neu einsammeln
    let moTimer = null;
    const observer = new MutationObserver(() => {{
        clearTimeout(moTimer);
        moTimer = setTimeout(collectCards, 150);
    }});
    observer.observe(doc.body, {{ childList: true, subtree: true }});

    function onMouseMove(e) {{
        mouseX = e.clientX;
        mouseY = e.clientY;
        mouseInside = true;
        spotTarget = 1;
        if (rafId === null) rafId = win.requestAnimationFrame(frame);
    }}

    function onMouseLeave() {{
        mouseInside = false;
        spotTarget = 0;
    }}

    const lerp = (a, b, t) => a + (b - a) * t;

    function frame() {{
        // --- Spotlight nachfuehren ---
        if (spotX < -9000) {{ spotX = mouseX; spotY = mouseY; }}
        spotX = lerp(spotX, mouseX, 0.18);
        spotY = lerp(spotY, mouseY, 0.18);
        spotOpacity = lerp(spotOpacity, spotTarget, 0.12);
        spotlight.style.left = spotX + 'px';
        spotlight.style.top = spotY + 'px';

        // Spotlight-Staerke haengt vom Abstand zur naechsten Karte ab
        let minDist = Infinity;
        let settled = Math.abs(spotOpacity - spotTarget) < 0.01;

        for (const card of cards) {{
            if (!card.isConnected) continue;
            const r = card.getBoundingClientRect();
            if (r.width === 0) continue;
            const cx = r.left + r.width / 2;
            const cy = r.top + r.height / 2;
            const dist = Math.hypot(mouseX - cx, mouseY - cy)
                         - Math.max(r.width, r.height) / 2;
            const d = Math.max(0, dist);
            minDist = Math.min(minDist, d);

            // --- Border-Glow (Proximity-Logik aus MagicBento) ---
            let glow = 0;
            if (mouseInside) {{
                if (d <= PROXIMITY) glow = 1;
                else if (d <= FADE_DISTANCE) {{
                    glow = (FADE_DISTANCE - d) / (FADE_DISTANCE - PROXIMITY);
                }}
            }}
            const relX = ((mouseX - r.left) / r.width) * 100;
            const relY = ((mouseY - r.top) / r.height) * 100;
            card.style.setProperty('--glow-x', relX.toFixed(1) + '%');
            card.style.setProperty('--glow-y', relY.toFixed(1) + '%');
            card.style.setProperty('--glow-intensity', glow.toFixed(3));

            // --- Tilt + Magnetism (nur bei Hover ueber der Karte) ---
            const s = cardState.get(card);
            const over = mouseInside &&
                mouseX >= r.left && mouseX <= r.right &&
                mouseY >= r.top && mouseY <= r.bottom;
            let trx = 0, try_ = 0, ttx = 0, tty = 0;
            if (over) {{
                const px = (mouseX - cx) / (r.width / 2);   // -1..1
                const py = (mouseY - cy) / (r.height / 2);
                trx = -py * TILT_DEG;
                try_ = px * TILT_DEG;
                ttx = (mouseX - cx) * MAGNETISM;
                tty = (mouseY - cy) * MAGNETISM;
            }}
            s.rx = lerp(s.rx, trx, 0.15);
            s.ry = lerp(s.ry, try_, 0.15);
            s.tx = lerp(s.tx, ttx, 0.15);
            s.ty = lerp(s.ty, tty, 0.15);
            if (Math.abs(s.rx) + Math.abs(s.ry) +
                Math.abs(s.tx) + Math.abs(s.ty) > 0.05) {{
                card.style.transform =
                    `perspective(1000px) rotateX(${{s.rx.toFixed(2)}}deg) ` +
                    `rotateY(${{s.ry.toFixed(2)}}deg) ` +
                    `translate(${{s.tx.toFixed(1)}}px, ${{s.ty.toFixed(1)}}px)`;
                settled = false;
            }} else if (card.style.transform) {{
                card.style.transform = '';
            }}
        }}

        // Spotlight dimmen, wenn keine Karte in Reichweite
        let targetOp = spotTarget;
        if (mouseInside && minDist < Infinity) {{
            if (minDist > FADE_DISTANCE) targetOp = 0;
            else if (minDist > PROXIMITY) {{
                targetOp = (FADE_DISTANCE - minDist) /
                           (FADE_DISTANCE - PROXIMITY);
            }}
        }}
        spotlight.style.opacity =
            (spotOpacity * Math.max(0.15, targetOp)).toFixed(3);

        if (!settled || spotOpacity > 0.01) {{
            rafId = win.requestAnimationFrame(frame);
        }} else {{
            rafId = null;
        }}
    }}

    // --- Click-Ripple ---
    function onClick(e) {{
        const card = e.target.closest && e.target.closest(CARD_SELECTOR);
        if (!card) return;
        const r = card.getBoundingClientRect();
        const maxDist = Math.max(
            Math.hypot(e.clientX - r.left, e.clientY - r.top),
            Math.hypot(e.clientX - r.right, e.clientY - r.top),
            Math.hypot(e.clientX - r.left, e.clientY - r.bottom),
            Math.hypot(e.clientX - r.right, e.clientY - r.bottom)
        );
        const ripple = doc.createElement('div');
        ripple.className = 'bento-ripple';
        ripple.style.width = ripple.style.height = maxDist * 2 + 'px';
        ripple.style.left = (e.clientX - r.left - maxDist) + 'px';
        ripple.style.top = (e.clientY - r.top - maxDist) + 'px';
        card.appendChild(ripple);
        ripple.addEventListener('animationend', () => ripple.remove());
    }}

    doc.addEventListener('mousemove', onMouseMove);
    doc.documentElement.addEventListener('mouseleave', onMouseLeave);
    doc.addEventListener('click', onClick);

    win.__bentoCleanup = function() {{
        doc.removeEventListener('mousemove', onMouseMove);
        doc.documentElement.removeEventListener('mouseleave', onMouseLeave);
        doc.removeEventListener('click', onClick);
        observer.disconnect();
        if (rafId !== null) win.cancelAnimationFrame(rafId);
        const old = doc.getElementById('bento-spotlight');
        if (old) old.remove();
    }};
}})();
</script>
"""


def inject_theme(effects: bool = True) -> None:
    """Injiziert das Bento-Theme (CSS) und optional die Maus-Effekte (JS)."""
    st.markdown(_CSS, unsafe_allow_html=True)
    if effects:
        components.html(_effects_js(), height=0)
