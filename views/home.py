import streamlit as st
import streamlit.components.v1 as components

CARTOON = """
<style>
  .wrap { display:flex; flex-direction:column; align-items:center; padding:1rem 0; }
  @keyframes shiver {
    0%,100% { transform: translate(0,0) rotate(0deg); }
    20% { transform: translate(-2px,1px) rotate(-1.5deg); }
    40% { transform: translate(2px,-1px) rotate(1.5deg); }
    60% { transform: translate(-2px,-1px) rotate(-1deg); }
    80% { transform: translate(2px,1px) rotate(1deg); }
  }
  @keyframes wag { 0%,100% { transform: skewY(-4deg); } 50% { transform: skewY(4deg); } }
  @keyframes fall { from { transform: translateY(-10px); opacity:0; } 20% { opacity:.9; }
                    to { transform: translateY(40px); opacity:0; } }
  .sperm { animation: shiver .18s infinite; transform-origin: 180px 150px; }
  .tail  { animation: wag .12s infinite; transform-origin: 300px 150px; }
  .flake { animation: fall 2.4s infinite; font-size:22px; fill:#9ad1ff; }
  .f2 { animation-delay:.8s } .f3 { animation-delay:1.6s }
</style>
<div class="wrap">
<svg viewBox="0 0 560 300" width="560" role="img" aria-label="Shivering spermatozoon holding a blank sign">
  <text class="flake" x="90"  y="40">❄</text>
  <text class="flake f2" x="260" y="30">❄</text>
  <text class="flake f3" x="470" y="45">❄</text>
  <g class="sperm">
    <!-- tail -->
    <g class="tail">
      <path d="M300 150 C 340 110, 380 190, 420 150 S 500 110, 540 150"
            fill="none" stroke="#7fb8e6" stroke-width="9" stroke-linecap="round"/>
    </g>
    <!-- head -->
    <ellipse cx="180" cy="150" rx="125" ry="70" fill="#cfe8fb" stroke="#4a86b8" stroke-width="5"/>
    <!-- face -->
    <circle cx="140" cy="135" r="13" fill="#fff" stroke="#2c5a7c" stroke-width="3"/>
    <circle cx="190" cy="135" r="13" fill="#fff" stroke="#2c5a7c" stroke-width="3"/>
    <circle cx="143" cy="138" r="5" fill="#2c5a7c"/>
    <circle cx="187" cy="138" r="5" fill="#2c5a7c"/>
    <path d="M135 180 q10 -10 20 0 q10 10 20 0 q10 -10 20 0 q10 10 20 0"
          fill="none" stroke="#2c5a7c" stroke-width="4" stroke-linecap="round"/>
    <ellipse cx="118" cy="162" rx="12" ry="7" fill="#8fc4f0" opacity=".6"/>
    <ellipse cx="212" cy="162" rx="12" ry="7" fill="#8fc4f0" opacity=".6"/>
    <!-- sign on the "shoulder" (neck) -->
    <line x1="300" y1="140" x2="318" y2="62" stroke="#8a6a43" stroke-width="6" stroke-linecap="round"/>
    <rect x="262" y="12" width="120" height="62" rx="6" fill="#fffdf4" stroke="#8a6a43" stroke-width="5"/>
    <text x="322" y="52" text-anchor="middle" font-size="26" fill="#bbb" font-family="monospace">_ _ _ _</text>
  </g>
</svg>
<p style="color:#4a86b8; font-style:italic; margin:0;">brrr… -196 °C and I still need a name tag.</p>
</div>
"""

st.title("🧊 Mouse Cryo Manager")
components.html(CARTOON, height=330)
st.markdown(
    "Use the sidebar to **submit** new straws or **search** the freezer inventory by line name."
)
