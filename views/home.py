import streamlit as st
import streamlit.components.v1 as components

CARTOON = """
<style>
  body { margin:0; font-family: 'Comic Sans MS', 'Segoe UI', sans-serif; }
  .wrap { display:flex; flex-direction:column; align-items:center; }
  @keyframes shiver {
    0%,100% { transform: translate(0,0) rotate(0deg); }
    20% { transform: translate(-3px,1px) rotate(-1.4deg); }
    40% { transform: translate(3px,-1px) rotate(1.4deg); }
    60% { transform: translate(-2.5px,-1.5px) rotate(-1deg); }
    80% { transform: translate(2.5px,1.5px) rotate(1deg); }
  }
  @keyframes fall { from { transform: translateY(-14px) rotate(0); opacity:0; }
                    15% { opacity:.95; } to { transform: translateY(470px) rotate(180deg); opacity:0; } }
  @keyframes chatter { 0%,100% { transform: translateY(0); } 50% { transform: translateY(5px); } }
  @keyframes buzz { 0%,100% { opacity:.25; } 50% { opacity:1; } }
  .sperm { animation: shiver .15s infinite; transform-origin: 200px 250px; }
  .flake { animation: fall 5s linear infinite; font-size:20px; fill:#bfe3ff; }
  .jaw   { animation: chatter .12s infinite; }
  .zz    { animation: buzz .3s infinite; } .zz2 { animation-delay:.15s; }
</style>
<div class="wrap">
<svg viewBox="0 0 400 480" width="320" role="img"
     aria-label="Shivering cartoon spermatozoon wrapped in a plaid blanket">
  <defs>
    <radialGradient id="headg" cx="38%" cy="28%" r="85%">
      <stop offset="0" stop-color="#ffffff"/><stop offset=".55" stop-color="#e3f3ff"/>
      <stop offset="1" stop-color="#a9d4f3"/>
    </radialGradient>
    <clipPath id="blanketclip">
      <path id="blanket" d="M96 252 Q200 292 304 252 L330 352 Q200 392 70 352 Z"/>
    </clipPath>
  </defs>

  <text class="flake" x="40"  y="0">❄</text>
  <text class="flake" style="animation-delay:1.4s" x="130" y="0">❅</text>
  <text class="flake" style="animation-delay:2.6s" x="330" y="0">❄</text>
  <text class="flake" style="animation-delay:.7s"  x="365" y="0">❅</text>
  <text class="flake" style="animation-delay:3.5s" x="250" y="0">❄</text>

  <g class="sperm">
    <!-- tail: outlined tube, waving -->
    <path fill="none" stroke="#111" stroke-width="29" stroke-linecap="round" stroke-linejoin="round">
      <animate attributeName="d" dur=".55s" repeatCount="indefinite"
        values="M200 300 C 200 345, 160 365, 176 405 S 214 440, 192 466;
                M200 300 C 200 345, 240 365, 224 405 S 186 440, 208 466;
                M200 300 C 200 345, 160 365, 176 405 S 214 440, 192 466"/>
    </path>
    <path fill="none" stroke="#d3eafb" stroke-width="19" stroke-linecap="round" stroke-linejoin="round">
      <animate attributeName="d" dur=".55s" repeatCount="indefinite"
        values="M200 300 C 200 345, 160 365, 176 405 S 214 440, 192 466;
                M200 300 C 200 345, 240 365, 224 405 S 186 440, 208 466;
                M200 300 C 200 345, 160 365, 176 405 S 214 440, 192 466"/>
    </path>

    <!-- head: fill, then open outline so the neck flows into the tail -->
    <path id="head" fill="url(#headg)"
      d="M200 18 C 266 18 306 92 306 165 C 306 226 266 256 224 284 Q 212 292 212 304
         L 188 304 Q 188 292 176 284 C 134 256 94 226 94 165 C 94 92 134 18 200 18 Z"/>
    <path fill="none" stroke="#111" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"
      d="M212 304 Q 212 292 224 284 C 266 256 306 226 306 165 C 306 92 266 18 200 18
         C 134 18 94 92 94 165 C 94 226 134 256 176 284 Q 188 292 188 304"/>
    <path d="M130 120 Q 140 70 185 48" fill="none" stroke="#fff" stroke-width="9"
          stroke-linecap="round" opacity=".85"/>

    <!-- eyes: big, round, looking worried -->
    <ellipse cx="161" cy="128" rx="23" ry="29" fill="#fff" stroke="#111" stroke-width="4.5"/>
    <ellipse cx="239" cy="128" rx="23" ry="29" fill="#fff" stroke="#111" stroke-width="4.5"/>
    <circle cx="156" cy="136" r="11" fill="#111"/><circle cx="234" cy="136" r="11" fill="#111"/>
    <circle cx="151" cy="131" r="4" fill="#fff"/><circle cx="229" cy="131" r="4" fill="#fff"/>
    <path d="M132 100 L 182 88 M268 100 L 218 88" stroke="#111" stroke-width="5.5" stroke-linecap="round"/>
    <!-- cheeks -->
    <ellipse cx="128" cy="184" rx="15" ry="9" fill="#ff9aa2" opacity=".7"/>
    <ellipse cx="272" cy="184" rx="15" ry="9" fill="#ff9aa2" opacity=".7"/>
    <!-- chattering mouth -->
    <path d="M160 200 Q200 190 240 200 Q 236 238 200 238 Q 164 238 160 200 Z"
          fill="#7a1f2b" stroke="#111" stroke-width="4.5" stroke-linejoin="round"/>
    <g class="jaw">
      <path d="M168 203 Q200 196 232 203 L 230 214 Q200 208 170 214 Z" fill="#fff" stroke="#111" stroke-width="2"/>
      <path d="M200 203 V 213 M184 201 V 211 M216 201 V 211" stroke="#111" stroke-width="2"/>
    </g>
    <!-- cold drop -->
    <path d="M292 120 q-10 18 0 26 q10 -8 0 -26 Z" fill="#8ec5ee" stroke="#111" stroke-width="3"/>

    <!-- blanket draped over the shoulders -->
    <g>
      <use href="#blanket" fill="#e8574a"/>
      <g clip-path="url(#blanketclip)">
        <g stroke="#fff3d6" stroke-width="7" opacity=".9">
          <path d="M60 282 H340 M60 316 H340 M60 350 H340"/>
        </g>
        <g stroke="#8f2a22" stroke-width="9" opacity=".55">
          <path d="M120 240 V 400 M165 240 V 400 M210 240 V 400 M255 240 V 400 M300 240 V 400"/>
        </g>
      </g>
      <use href="#blanket" fill="none" stroke="#111" stroke-width="5" stroke-linejoin="round"/>
      <!-- fluffy collar roll along the neckline -->
      <path d="M100 254 Q200 294 300 254" fill="none" stroke="#111" stroke-width="22" stroke-linecap="round"/>
      <path d="M100 254 Q200 294 300 254" fill="none" stroke="#ff8a7c" stroke-width="13" stroke-linecap="round"/>
      <!-- fringe -->
      <g stroke="#111" stroke-width="3.5" stroke-linecap="round">
        <path d="M82 357 l-2 14 M104 362 l-2 14 M126 366 l-1 14 M148 369 v14 M170 371 v14 M192 372 v14
                 M214 372 v14 M236 371 v14 M258 369 v14 M280 366 l1 14 M302 362 l2 14 M324 357 l2 14"/>
      </g>
    </g>
  </g>

  <!-- shiver marks -->
  <g class="zz" stroke="#4a86b8" stroke-width="5" stroke-linecap="round" fill="none">
    <path d="M62 120 q-8 8 0 16 q8 8 0 16"/><path d="M42 124 q-8 8 0 16 q8 8 0 16"/>
  </g>
  <g class="zz zz2" stroke="#4a86b8" stroke-width="5" stroke-linecap="round" fill="none">
    <path d="M338 120 q8 8 0 16 q-8 8 0 16"/><path d="M358 124 q8 8 0 16 q-8 8 0 16"/>
  </g>
  <text x="14" y="86" font-size="26" fill="#4a86b8" font-style="italic" transform="rotate(-12 14 86)">brrr!</text>
</svg>
<p style="color:#4a86b8; font-style:italic; margin:0;">-196 °C… somebody pass me a blanket. (Thanks, I got one.)</p>
</div>
"""

st.markdown("<h1 style='text-align:center'>Mouse Cryo Manager</h1>", unsafe_allow_html=True)
components.html(CARTOON, height=470)
st.markdown(
    "Use the sidebar to **freeze** new straws, **warm up** (thaw) existing ones, or **search** the inventory by line name."
)
