import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from src.utils import do_geocode, nearest_idx, to_celsius
from src.plotting import make_heatmap, make_timeseries
from src.config import GEMINI_API_KEY

EVENTS = {
    "2003 European Heatwave": {
        "year": "2003-08", "lat": 48.8, "lon": 2.3, "city": "Paris",
        "emoji": "🌡️",
        "color": "#ef4444",
        "desc": "Summer 2003 · +6°C anomaly · ~70,000 deaths across Europe",
        "stats": [("", "Peak Anomaly", "+6 °C above normal"),
                  ("", "Lives Lost", "~70,000 people"),
                  ("", "Countries Hit", "12 European nations"),
                  ("", "Duration", "June – August 2003")],
        "what":   "Temperatures across France, Germany, Spain and Italy surged 6°C above the seasonal normal for nearly three months.",
        "why":    "A stationary high-pressure dome trapped hot air over the continent, blocking the usual Atlantic weather systems that bring cooling rain.",
        "impact": "Crops failed, rivers dried up, and power plants had to throttle back because rivers used for cooling were too warm. Hospitals were overwhelmed."
    },
    "2010 Pakistan Floods": {
        "year": "2010-07", "lat": 30.3, "lon": 66.9, "city": "Quetta",
        "emoji": "🌊",
        "color": "#60a5fa",
        "desc": "Monsoon 2010 · 20 million displaced · worst flood on record",
        "stats": [("", "Rainfall", "3× the normal monsoon"),
                  ("", "Displaced", "20 million people"),
                  ("", "Homes Destroyed", "1.9 million"),
                  ("", "Duration", "July – September 2010")],
        "what":   "Record monsoon rains fell for weeks across Pakistan, swelling the Indus River to historic widths — flooding nearly one-fifth of the entire country.",
        "why":    "An unusually intense La Niña event supercharged the monsoon season, while deforestation on hillsides removed the natural sponge that would have absorbed some of the water.",
        "impact": "About 2,000 people died and 20 million lost their homes. Crops worth billions were lost, pushing food prices sky-high for months."
    },
    "2022 India Heatwave": {
        "year": "2022-04", "lat": 25.3, "lon": 83.0, "city": "Varanasi",
        "emoji": "☀️",
        "color": "#f59e0b",
        "desc": "April 2022 · +4.9°C above normal · 122-year record broken",
        "stats": [("🌡️", "Temp Anomaly", "+4.9 °C above normal"),
                  ("", "Record", "Hottest March in 122 years"),
                  ("", "Power Crisis", "Widespread grid failures"),
                  ("", "Wheat Yield", "Down 3–5% nationally")],
        "what":   "India and Pakistan experienced their hottest March and April since records began in 1900 — with temperatures crossing 45 °C weeks earlier than usual.",
        "why":    "A combination of a persistent anticyclone and long-term warming from greenhouse gases made this event 30× more likely than it would have been in a pre-industrial climate.",
        "impact": "Schools closed, outdoor workers faced life-threatening conditions, and an early heat stress on wheat crops forced the government to restrict grain exports."
    },
}

def render_story(ds, times):
    st.markdown('<div class="sec-header"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>Guided Climate Stories</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.92rem;color:#94a3b8;line-height:1.7;margin-bottom:1.2rem;">
      Pick a real climate disaster below. You'll see it highlighted on the global map, read a plain-English
      breakdown of what happened, and get an instant AI-written explanation a 10-year-old can understand.
    </div>
    """, unsafe_allow_html=True)

    ev_c1, ev_c2, ev_c3 = st.columns(3)
    for ev_col, ev_name in zip([ev_c1, ev_c2, ev_c3], list(EVENTS.keys())):
        with ev_col:
            ev = EVENTS[ev_name]
            ev_active = st.session_state.sel_event == ev_name
            border_color = ev["color"] if ev_active else "rgba(255,255,255,0.08)"
            glow = f"box-shadow:0 0 18px {ev['color']}44;" if ev_active else ""
            st.markdown(f"""
            <div style="background:#0f1219;border:2px solid {border_color};border-radius:12px;
                        padding:1rem 1.1rem;margin-bottom:6px;{glow}cursor:pointer;">
              <div style="font-size:1.8rem;line-height:1;margin-bottom:0.4rem">{ev['emoji']}</div>
              <div style="font-size:0.88rem;font-weight:700;color:#fff;margin-bottom:0.3rem">{ev_name}</div>
              <div style="font-size:0.75rem;color:#94a3b8;line-height:1.6">{ev['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(
                "Select" if not ev_active else "Selected",
                key=f"ev_{ev_name}",
                type="primary" if ev_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.sel_event = ev_name
                st.session_state.story_text = ""
                st.rerun()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    sel_ev_name = st.session_state.sel_event
    sel_ev = EVENTS[sel_ev_name]
    time_strs = [str(t)[:7] for t in times]
    ev_idx = time_strs.index(sel_ev["year"]) if sel_ev["year"] in time_strs else len(times) // 2

    stat_cols = st.columns(len(sel_ev["stats"]))
    for sc, (ico, lbl, val) in zip(stat_cols, sel_ev["stats"]):
        with sc:
            st.markdown(f"""
            <div style="background:#0f1219;border:1px solid {sel_ev['color']}44;border-radius:10px;
                        padding:0.9rem 1rem;text-align:center;border-top:3px solid {sel_ev['color']};">
              <div style="font-size:1.5rem;line-height:1;margin-bottom:0.3rem">{ico}</div>
              <div style="font-size:1.05rem;font-weight:700;color:#fff;margin-bottom:0.2rem">{val}</div>
              <div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    story_left, story_right = st.columns([3, 2])
    with story_left:
        fig_ev = make_heatmap(ds, "t2m", ev_idx,
                               title=f"{sel_ev_name} · {sel_ev['year']}",
                               cs=[[0,"#1d4ed8"],[0.33,"#4ade80"],[0.66,"#f59e0b"],[1,"#dc2626"]])
        fig_ev.add_trace(go.Scattergeo(
            lat=[sel_ev["lat"]], lon=[sel_ev["lon"]],
            mode="markers+text",
            marker=dict(size=16, color=sel_ev["color"], symbol="star",
                        line=dict(color="#0f1117", width=2)),
            text=[sel_ev["city"]],
            textposition="top right",
            textfont=dict(color=sel_ev["color"], size=12, family="Inter"),
            showlegend=False,
        ))
        st.plotly_chart(fig_ev, use_container_width=True)
        st.caption("Map shows global temperature for the event month. Star = disaster epicentre.")

    with story_right:
        st.markdown(f"""
        <div style="background:#0a0c12;border:1px solid {sel_ev['color']}33;border-left:3px solid {sel_ev['color']};
                    border-radius:0 12px 12px 0;padding:1.2rem 1.4rem;margin-bottom:1rem;">
          <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
                      color:{sel_ev['color']};margin-bottom:0.5rem;">📖 What Happened?</div>
          <div style="font-size:0.92rem;color:#e2e8f0;line-height:1.75;margin-bottom:0.8rem">{sel_ev['what']}</div>
          <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:0.8rem"></div>
          <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
                      color:{sel_ev['color']};margin-bottom:0.4rem;">🔬 Why Did It Happen?</div>
          <div style="font-size:0.92rem;color:#e2e8f0;line-height:1.75;margin-bottom:0.8rem">{sel_ev['why']}</div>
          <div style="height:1px;background:rgba(255,255,255,0.06);margin-bottom:0.8rem"></div>
          <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;
                      color:{sel_ev['color']};margin-bottom:0.4rem;">🌍 Human Impact</div>
          <div style="font-size:0.92rem;color:#e2e8f0;line-height:1.75">{sel_ev['impact']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="font-size:0.7rem;color:#f59e0b;font-weight:600;letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:0.4rem;">🤖 AI Deep-Dive</div>
        """, unsafe_allow_html=True)

        if st.button("Generate AI Explanation", type="primary", use_container_width=True):
            with st.spinner("Asking Gemini AI to explain this in plain English…"):
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                    prompt = (
                        f"The climate event '{sel_ev_name}' is visible in ERA5 data near "
                        f"{sel_ev['city']} in {sel_ev['year']}. In exactly 3 plain-English "
                        f"sentences: (1) what happened physically, (2) why it happened "
                        f"climatically, (3) human impact. No bullets. No jargon."
                    )
                    payload = {"contents": [{"parts": [{"text": prompt}]}]}
                    resp = requests.post(url, json=payload, timeout=20)
                    resp.raise_for_status()
                    st.session_state.story_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as err:
                    st.session_state.story_text = f"AI Error: {err}"

        if st.session_state.story_text:
            icon = "⚠️" if st.session_state.story_text.startswith("⚠️") else "🤖"
            color_ai = "#f59e0b" if st.session_state.story_text.startswith("⚠️") else "#4ade80"
            st.markdown(f"""
            <div class="ai-box" style="border-left-color:{color_ai};margin-top:0.8rem;">
              <span class="ai-box-label" style="color:{color_ai}">AI Analysis</span>
              {st.session_state.story_text}
            </div>
            """, unsafe_allow_html=True)

        # ── Voice Narrator ─────────────────────────────────────────────────────
        st.markdown("""
        <div style="font-size:0.7rem;color:#a78bfa;font-weight:600;letter-spacing:0.1em;
                    text-transform:uppercase;margin-top:1rem;margin-bottom:0.4rem;">Voice Narrator</div>
        """, unsafe_allow_html=True)

        import json as _json
        import streamlit.components.v1 as components

        # Build narration ONLY from text visible on screen — no AI improvisation
        _narration_parts = [
            f"Climate Story: {sel_ev_name}.",
            f"What happened: {sel_ev['what']}",
            f"Why it happened: {sel_ev['why']}",
            f"Human impact: {sel_ev['impact']}",
        ]
        if st.session_state.story_text and not st.session_state.story_text.startswith("⚠️"):
            # Strip any HTML tags from AI text before reading aloud
            import re as _re
            _clean_ai = _re.sub(r'<[^>]+>', '', st.session_state.story_text).strip()
            if _clean_ai:
                _narration_parts.append(f"AI Analysis: {_clean_ai}")

        # json.dumps gives a JS-safe quoted string — handles quotes, backticks, newlines, all special chars
        _narration_js = _json.dumps(" ".join(_narration_parts))

        components.html(f"""
        <style>
          .vn-wrap {{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-family:Inter,sans-serif;}}
          .vn-btn {{border:none;border-radius:8px;padding:7px 16px;font-size:0.82rem;font-weight:700;cursor:pointer;transition:opacity .15s;}}
          .vn-btn:hover {{opacity:0.85;}}
          .vn-play  {{background:#a78bfa;color:#0f1117;}}
          .vn-pause {{background:#60a5fa;color:#0f1117;}}
          .vn-stop  {{background:#374151;color:#e2e8f0;}}
          .vn-speed {{background:#0f1219;color:#8896aa;border:1px solid #2a3444;border-radius:8px;padding:6px 10px;font-size:0.8rem;cursor:pointer;}}
          .vn-status {{font-size:0.72rem;color:#94a3b8;margin-top:5px;display:flex;align-items:center;gap:6px;}}
          .vn-dot {{width:8px;height:8px;border-radius:50%;background:#6b7280;display:inline-block;}}
          .vn-dot.playing {{background:#a78bfa;animation:vnpulse 1s infinite;}}
          @keyframes vnpulse {{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
        </style>
        <div class="vn-wrap">
          <button class="vn-btn vn-play"  id="btnPlay"   onclick="startNarration()">&#9654; Play Narration</button>
          <button class="vn-btn vn-pause" id="btnPause"  onclick="pauseNarration()"  style="display:none">&#9208; Pause</button>
          <button class="vn-btn vn-pause" id="btnResume" onclick="resumeNarration()" style="display:none">&#9654; Resume</button>
          <button class="vn-btn vn-stop"                onclick="stopNarration()">&#9724; Stop</button>
          <select class="vn-speed" id="speedSel" onchange="changeSpeed(this.value)">
            <option value="0.8">Slow</option>
            <option value="1.0" selected>Normal</option>
            <option value="1.3">Fast</option>
          </select>
        </div>
        <div class="vn-status" id="vnStatus">
          <span class="vn-dot" id="vnDot"></span>
          <span id="vnLabel">Ready — will read exactly what is shown on screen</span>
        </div>
        <script>
        const NARRATION = {_narration_js};
        let utterance = null;
        let currentRate = 1.0;
        function getVoice() {{
          const voices = window.speechSynthesis.getVoices();
          return (
            voices.find(v => v.name === 'Google UK English Female') ||
            voices.find(v => v.name === 'Google US English') ||
            voices.find(v => v.name.includes('Natural') && v.lang.startsWith('en')) ||
            voices.find(v => v.lang === 'en-US') ||
            voices.find(v => v.lang.startsWith('en')) || null
          );
        }}
        function setStatus(label, isPlaying) {{
          document.getElementById('vnLabel').textContent = label;
          document.getElementById('vnDot').classList.toggle('playing', isPlaying);
        }}
        function startNarration() {{
          window.speechSynthesis.cancel();
          utterance = new SpeechSynthesisUtterance(NARRATION);
          utterance.rate = currentRate; utterance.pitch = 1.0; utterance.lang = 'en-US';
          const v = getVoice(); if (v) utterance.voice = v;
          utterance.onstart = () => {{
            setStatus('Narrating on-screen text...', true);
            document.getElementById('btnPlay').style.display   = 'none';
            document.getElementById('btnPause').style.display  = 'inline-block';
            document.getElementById('btnResume').style.display = 'none';
          }};
          utterance.onend = () => {{
            setStatus('Done', false);
            document.getElementById('btnPlay').style.display   = 'inline-block';
            document.getElementById('btnPause').style.display  = 'none';
            document.getElementById('btnResume').style.display = 'none';
          }};
          utterance.onerror = (e) => {{
            setStatus('Error: ' + e.error, false);
            document.getElementById('btnPlay').style.display = 'inline-block';
            document.getElementById('btnPause').style.display = document.getElementById('btnResume').style.display = 'none';
          }};
          if (window.speechSynthesis.getVoices().length === 0)
            window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.speak(utterance);
          else window.speechSynthesis.speak(utterance);
        }}
        function pauseNarration() {{
          if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {{
            window.speechSynthesis.pause(); setStatus('Paused', false);
            document.getElementById('btnPause').style.display  = 'none';
            document.getElementById('btnResume').style.display = 'inline-block';
          }}
        }}
        function resumeNarration() {{
          if (window.speechSynthesis.paused) {{
            window.speechSynthesis.resume(); setStatus('Narrating on-screen text...', true);
            document.getElementById('btnPause').style.display  = 'inline-block';
            document.getElementById('btnResume').style.display = 'none';
          }}
        }}
        function stopNarration() {{
          window.speechSynthesis.cancel(); setStatus('Stopped', false);
          document.getElementById('btnPlay').style.display   = 'inline-block';
          document.getElementById('btnPause').style.display  = document.getElementById('btnResume').style.display = 'none';
        }}
        function changeSpeed(val) {{
          currentRate = parseFloat(val);
          if (window.speechSynthesis.speaking) {{ stopNarration(); startNarration(); }}
        }}
        </script>
        """, height=90)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-header"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>Explore Any City</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.88rem;color:#94a3b8;margin-bottom:1rem;line-height:1.6">
      Type any city name, pick a year — see its full 30-year temperature story with an optional AI interpretation.
    </div>
    """, unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([3, 1, 1])
    with fc1:
        free_city = st.text_input("City", placeholder="e.g. Mumbai, London, Tokyo…", label_visibility="collapsed")
    with fc2:
        free_yr = st.selectbox("Year", list(range(1990, 2023)), index=25)
    with fc3:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        explore_btn = st.button("Explore", type="primary", use_container_width=True)

    if free_city and explore_btn:
        lat_fc, lon_fc = do_geocode(free_city)
        if lat_fc is not None:
            yr_strs = [str(t)[:4] for t in times]
            yr_idx = next((i for i, y in enumerate(yr_strs) if y == str(free_yr)), 0)
            li, lj = nearest_idx(ds, lat_fc, lon_fc)

            city_temp_yr  = float(to_celsius(ds["t2m"].isel(time=yr_idx, latitude=li, longitude=lj)))
            city_all      = to_celsius(ds["t2m"].isel(latitude=li, longitude=lj))
            city_mean_all = float(city_all.mean())
            city_max_all  = float(city_all.max())
            city_min_all  = float(city_all.min())
            delta_yr      = city_temp_yr - city_mean_all
            delta_sign    = "+" if delta_yr >= 0 else ""
            delta_color   = "#ef4444" if delta_yr > 0.5 else "#4ade80" if delta_yr < -0.5 else "#f59e0b"

            sc1, sc2, sc3, sc4 = st.columns(4)
            for sc, ico, lbl, val, col in [
                (sc1, "", f"Temp in {free_yr}", f"{city_temp_yr:.1f}°C", "#60a5fa"),
                (sc2, "", "30-yr Average",       f"{city_mean_all:.1f}°C", "#4ade80"),
                (sc3, "", "All-time High",         f"{city_max_all:.1f}°C", "#ef4444"),
                (sc4, "", "All-time Low",           f"{city_min_all:.1f}°C", "#60a5fa"),
            ]:
                with sc:
                    st.markdown(f"""
                    <div style="background:#0f1219;border:1px solid {col}44;border-top:2px solid {col};
                                border-radius:10px;padding:0.8rem;text-align:center;margin-bottom:0.6rem;">
                      <div style="font-size:1.4rem">{ico}</div>
                      <div style="font-size:1rem;font-weight:700;color:#fff">{val}</div>
                      <div style="font-size:0.68rem;color:#94a3b8;text-transform:uppercase">{lbl}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="font-size:0.82rem;color:{delta_color};font-weight:600;margin-bottom:0.8rem;
                        padding:0.45rem 0.8rem;background:{delta_color}10;border-radius:8px;
                        border-left:3px solid {delta_color};">
              {free_city} in {free_yr} was <b>{delta_sign}{delta_yr:.1f}°C</b>
              {'warmer' if delta_yr > 0 else 'cooler'} than the 30-year average for this location.
            </div>
            """, unsafe_allow_html=True)

            st.plotly_chart(
                make_timeseries(ds, "t2m", li, lj, label=free_city,
                                color="#f59e0b", fillcolor="rgba(245,158,11,0.06)"),
                use_container_width=True,
            )
            st.caption(
                "Monthly values shown · Bold = 12-month average · Dotted = trend."
            )

            with st.spinner("Generating AI climate insight…"):
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                    prompt_ex = (
                        f"For {free_city}, ERA5 data shows an average temperature of "
                        f"{city_temp_yr:.1f}°C in {free_yr} vs a 30-year mean of "
                        f"{city_mean_all:.1f}°C. In 3 plain-English sentences: what this "
                        f"means climatically, any regional trend, and why someone living "
                        f"there should care."
                    )
                    payload_ex = {"contents": [{"parts": [{"text": prompt_ex}]}]}
                    r_ex = requests.post(url, json=payload_ex, timeout=20)
                    r_ex.raise_for_status()
                    insight_text = r_ex.json()["candidates"][0]["content"]["parts"][0]["text"]
                    st.markdown(f"""
                    <div class="ai-box">
                      <span class="ai-box-label">🤖 AI Insight for {free_city}</span>
                      {insight_text}
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as err:
                    st.error(f"Gemini API error: {err}")
        else:
            st.warning("City not found. Try a different spelling or a larger nearby city.")