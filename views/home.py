import streamlit as st
import streamlit.components.v1 as components

CARTOON = """
<style>
  body { margin:0; font-family: 'Comic Sans MS', 'Segoe UI', sans-serif; }
  .wrap { display:flex; flex-direction:column; align-items:center; }
  @keyframes shiver {
    0%,100% { transform: translate(0,0) rotate(0deg); }
    20% { transform: translate(-2.5px,1px) rotate(-1.2deg); }
    40% { transform: translate(2.5px,-1px) rotate(1.2deg); }
    60% { transform: translate(-2px,-1.5px) rotate(-.8deg); }
    80% { transform: translate(2px,1.5px) rotate(.8deg); }
  }
  @keyframes fall { from { transform: translateY(-14px) rotate(0); opacity:0; }
                    15% { opacity:.95; } to { transform: translateY(300px) rotate(180deg); opacity:0; } }
  @keyframes chatter { 0%,100% { transform: scaleY(1); } 50% { transform: scaleY(.35); } }
  @keyframes puff { 0% { transform: translate(0,0) scale(.4); opacity:0; }
                    30% { opacity:.8; } 100% { transform: translate(-26px,-22px) scale(1.2); opacity:0; } }
  @keyframes twinkle { 0%,100% { opacity:.2; } 50% { opacity:1; } }
  .sperm { animation: shiver .16s infinite; transform-origin: 230px 170px; }
  .flake { animation: fall 4.5s linear infinite; font-size:20px; fill:#bfe3ff; }
  .teeth { animation: chatter .12s infinite; transform-box: fill-box; transform-origin: center; }
  .puff  { animation: puff 2.2s ease-out infinite; transform-box: fill-box; transform-origin: center; }
  .p2 { animation-delay:1.1s }
  .tw { animation: twinkle 1.8s infinite; } .tw2 { animation-delay:.6s } .tw3 { animation-delay:1.2s }
</style>
<div class="wrap">
<svg viewBox="0 0 640 330" width="640" role="img"
     aria-label="Shivering spermatozoon with beanie and scarf holding a blank sign">
  <defs>
    <radialGradient id="bg" cx="50%" cy="45%" r="65%">
      <stop offset="0" stop-color="#eaf6ff"/><stop offset="1" stop-color="#d3ecff" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="head" cx="35%" cy="30%" r="80%">
      <stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#d9efff"/>
      <stop offset="1" stop-color="#8ec5ee"/>
    </radialGradient>
    <linearGradient id="tailg" x1="0" x2="1">
      <stop offset="0" stop-color="#5a9fd0"/><stop offset="1" stop-color="#a6d2f2"/>
    </linearGradient>
  </defs>

  <ellipse cx="320" cy="170" rx="310" ry="150" fill="url(#bg)"/>
  <text class="flake" x="70"  y="0">❄</text>
  <text class="flake" style="animation-delay:1.3s" x="190" y="0">❅</text>
  <text class="flake" style="animation-delay:2.4s" x="420" y="0">❄</text>
  <text class="flake" style="animation-delay:.6s"  x="560" y="0">❅</text>
  <text class="flake" style="animation-delay:3.2s" x="320" y="0">❄</text>

  <!-- ice floor -->
  <path d="M40 300 Q320 275 600 300 L600 318 Q320 340 40 318 Z" fill="#cfe8fb" opacity=".7"/>
  <path d="M100 300 l8 22 l8 -22 M210 296 l6 16 l6 -16 M440 296 l8 20 l8 -20 M530 300 l6 14 l6 -14"
        fill="#e8f5ff" stroke="#9ccbee" stroke-width="2" stroke-linejoin="round"/>
  <text class="tw" x="70" y="290" font-size="16" fill="#7fb8e6">✦</text>
  <text class="tw tw2" x="560" y="285" font-size="14" fill="#7fb8e6">✦</text>
  <text class="tw tw3" x="330" y="312" font-size="12" fill="#7fb8e6">✦</text>

  <g class="sperm">
    <!-- tail: midpiece (thick) + principal piece (tapering wave) -->
    <path fill="none" stroke="url(#tailg)" stroke-width="16" stroke-linecap="round">
      <animate attributeName="d" dur=".5s" repeatCount="indefinite"
        values="M330 190 C 370 160, 400 220, 440 190 S 510 160, 560 195 S 600 215, 620 200;
                M330 190 C 370 220, 400 160, 440 190 S 510 225, 560 190 S 600 175, 620 200;
                M330 190 C 370 160, 400 220, 440 190 S 510 160, 560 195 S 600 215, 620 200"/>
    </path>
    <path fill="none" stroke="#2f6f9f" stroke-width="3" stroke-dasharray="2 10" stroke-linecap="round" opacity=".7">
      <animate attributeName="d" dur=".5s" repeatCount="indefinite"
        values="M330 190 C 370 160, 400 220, 440 190 S 510 160, 560 195 S 600 215, 620 200;
                M330 190 C 370 220, 400 160, 440 190 S 510 225, 560 190 S 600 175, 620 200;
                M330 190 C 370 160, 400 220, 440 190 S 510 160, 560 195 S 600 215, 620 200"/>
    </path>

    <!-- head -->
    <ellipse cx="215" cy="175" rx="125" ry="88" fill="url(#head)" stroke="#3f7fae" stroke-width="5"/>
    <path d="M110 150 Q125 110 175 100" fill="none" stroke="#fff" stroke-width="8"
          stroke-linecap="round" opacity=".8"/>

    <!-- beanie -->
    <path d="M122 128 Q130 62 215 58 Q300 62 308 128 Q215 108 122 128 Z" fill="#ff7a6b" stroke="#b9473b" stroke-width="4"/>
    <path d="M120 124 Q215 104 310 124 L306 142 Q215 122 124 142 Z" fill="#ffb199" stroke="#b9473b" stroke-width="4"/>
    <g stroke="#b9473b" stroke-width="2.5" opacity=".6">
      <path d="M160 70 L168 112 M200 62 L202 108 M240 62 L238 108 M274 74 L266 112"/>
    </g>
    <circle cx="215" cy="52" r="15" fill="#fff4ef" stroke="#b9473b" stroke-width="4"/>

    <!-- face: eyes -->
    <ellipse cx="170" cy="168" rx="19" ry="23" fill="#fff" stroke="#24506f" stroke-width="3.5"/>
    <ellipse cx="248" cy="168" rx="19" ry="23" fill="#fff" stroke="#24506f" stroke-width="3.5"/>
    <circle cx="165" cy="174" r="9" fill="#24506f"/><circle cx="243" cy="174" r="9" fill="#24506f"/>
    <circle cx="161" cy="170" r="3.2" fill="#fff"/><circle cx="239" cy="170" r="3.2" fill="#fff"/>
    <!-- worried brows -->
    <path d="M148 152 L186 140 M270 152 L232 140" stroke="#24506f" stroke-width="5" stroke-linecap="round"/>
    <!-- cheeks + rosy nose -->
    <ellipse cx="140" cy="206" rx="15" ry="9" fill="#ff9aa2" opacity=".65"/>
    <ellipse cx="278" cy="206" rx="15" ry="9" fill="#ff9aa2" opacity=".65"/>
    <!-- chattering mouth -->
    <path d="M178 222 Q209 244 240 222 Q209 232 178 222 Z" fill="#24506f"/>
    <g class="teeth"><rect x="190" y="223" width="12" height="9" rx="2" fill="#fff"/>
                      <rect x="206" y="223" width="12" height="9" rx="2" fill="#fff"/>
                      <rect x="222" y="223" width="10" height="8" rx="2" fill="#fff"/></g>
    <!-- sweat / cold drop -->
    <path d="M318 150 q-8 14 0 20 q8 -6 0 -20 Z" fill="#8ec5ee" stroke="#3f7fae" stroke-width="2"/>

    <!-- scarf at the neck/shoulder -->
    <path d="M312 150 Q338 175 322 222 L296 214 Q312 180 296 156 Z" fill="#5cb85c" stroke="#2f7d32" stroke-width="4"/>
    <path d="M302 164 l22 8 M306 184 l22 6 M304 204 l20 4" stroke="#fff" stroke-width="4" opacity=".8"/>
    <path d="M310 218 Q316 262 296 276 L276 262 Q292 250 290 216 Z" fill="#5cb85c" stroke="#2f7d32" stroke-width="4"/>
    <path d="M286 236 l16 5 M287 252 l14 4" stroke="#fff" stroke-width="4" opacity=".8"/>

    <!-- sign held on the shoulder -->
    <line x1="334" y1="180" x2="372" y2="70" stroke="#8a6a43" stroke-width="7" stroke-linecap="round"/>
    <rect x="320" y="14" width="150" height="72" rx="8" fill="#fffdf4" stroke="#8a6a43" stroke-width="6"
          transform="rotate(4 395 50)"/>
    <path d="M338 58 H452" stroke="#d9d4c3" stroke-width="3.5" stroke-dasharray="3 7" stroke-linecap="round"
          transform="rotate(4 395 50)"/>
    <circle cx="338" cy="24" r="3" fill="#8a6a43"/><circle cx="454" cy="30" r="3" fill="#8a6a43"/>
    <!-- mitten holding pole -->
    <circle cx="336" cy="178" r="12" fill="#ff7a6b" stroke="#b9473b" stroke-width="4"/>
  </g>

  <!-- cold breath -->
  <g fill="#fff" stroke="#9ccbee" stroke-width="2">
    <circle class="puff" cx="90" cy="230" r="10"/><circle class="puff p2" cx="80" cy="238" r="7"/>
  </g>
  <text x="30" y="214" font-size="22" fill="#4a86b8" font-style="italic" transform="rotate(-10 30 214)">brrr!</text>
  <g stroke="#4a86b8" stroke-width="4" stroke-linecap="round" opacity=".7">
    <path d="M78 130 l-14 -6 M72 160 l-18 0 M78 190 l-14 6"/>
  </g>
</svg>
<p style="color:#4a86b8; font-style:italic; margin:4px 0 0;">-196 °C and I still need a name tag.</p>
</div>
"""

st.markdown("<h1 style='text-align:center'>Mouse Cryo Manager</h1>", unsafe_allow_html=True)
components.html(CARTOON, height=390)
st.markdown(
    "Use the sidebar to **freeze** new straws, **warm up** (thaw) existing ones, or **search** the inventory by line name."
)
