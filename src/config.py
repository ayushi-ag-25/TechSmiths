import os 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY",'AIzaSyCKtaOPDnWAtz2w-0K79JL4KHvTGkRysak')
CLIM_CS = [
    [0.0,  "#1a7340"],
    [0.25, "#4ade80"],
    [0.5,  "#fde047"],
    [0.75, "#f97316"],
    [1.0,  "#dc2626"],
]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Sans:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg:  #0f1117;
  --bg2: #181c27;
  --bg3: #1e2333;
  --card: #1a1f2e;
  --border: rgba(255,255,255,0.08);
  --border-hover: rgba(255,255,255,0.18);
  --accent: #4ade80;       /* green */
  --accent2: #f59e0b;      /* amber */
  --accent3: #ef4444;      /* red */
  --blue: #60a5fa;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --faint: #475569;
}

/* Reset & base */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; background: var(--bg) !important; color: var(--text) !important; }
.stApp { background: var(--bg) !important; }
.block-container { padding: 1.5rem 2rem 3rem !important; max-width: 1440px !important; }
#MainMenu, footer, header { visibility: hidden !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { font-family: 'Inter', sans-serif !important; }

/* ── HERO BANNER ── */
.hero {
  background: linear-gradient(135deg, #0d1b2a 0%, #111827 60%, #0a0f1e 100%);
  border: 1px solid rgba(74, 222, 128, 0.2);
  border-radius: 16px;
  padding: 2rem 2.5rem 1.8rem;
  margin-bottom: 1.5rem;
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, transparent, #4ade80, #f59e0b, transparent);
  border-radius: 16px 16px 0 0;
}
.hero-eyebrow {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 8px;
}
.hero-eyebrow .dot { width: 6px; height: 6px; background: var(--accent); border-radius: 50%; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(1.3)} }
.hero-title {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 2.6rem !important;
  font-weight: 700 !important;
  color: #fff !important;
  margin: 0 0 0.3rem !important;
  letter-spacing: -0.5px;
  line-height: 1.1;
}
.hero-title span { color: var(--accent); }
.hero-sub { font-size: 1rem; color: var(--muted); margin-top: 0.2rem; font-weight: 400; line-height: 1.6; }
.hero-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 1rem; }
.chip {
  font-size: 0.7rem; font-weight: 500; letter-spacing: 0.05em;
  padding: 4px 12px; border-radius: 20px; border: 1px solid;
  display: inline-flex; align-items: center; gap: 5px;
}
.chip-g { border-color: rgba(74,222,128,.35); color: #4ade80; background: rgba(74,222,128,.06); }
.chip-a { border-color: rgba(245,158,11,.35); color: #f59e0b; background: rgba(245,158,11,.06); }
.chip-b { border-color: rgba(96,165,250,.35); color: #60a5fa; background: rgba(96,165,250,.06); }

/* ── MODE TABS ── */
.stButton > button {
  font-family: 'Inter', sans-serif !important;
  font-weight: 500 !important;
  font-size: 0.88rem !important;
  letter-spacing: 0.02em !important;
  border-radius: 10px !important;
  border: 1px solid var(--border) !important;
  background: var(--bg2) !important;
  color: var(--muted) !important;
  padding: 0.6rem 1.2rem !important;
  transition: all 0.2s !important;
}
.stButton > button:hover {
  border-color: var(--border-hover) !important;
  color: var(--text) !important;
  background: var(--bg3) !important;
  transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"] {
  background: rgba(74,222,128,0.1) !important;
  border-color: rgba(74,222,128,0.4) !important;
  color: var(--accent) !important;
  box-shadow: 0 0 20px rgba(74,222,128,0.1) !important;
}

/* ── INPUTS ── */
.stSelectbox label, .stSlider label, .stTextInput label {
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  color: var(--muted) !important;
  letter-spacing: 0.04em !important;
  text-transform: none !important;
}
.stSelectbox > div > div {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}
.stTextInput > div > div > input {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  font-size: 0.92rem !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(74,222,128,0.15) !important;
  outline: none !important;
}

/* ── CARDS ── */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.1rem 1.3rem;
  margin-bottom: 10px;
  position: relative;
}
.card-max { border-left: 3px solid #ef4444; }
.card-mean { border-left: 3px solid #f59e0b; }
.card-min { border-left: 3px solid #60a5fa; }
.card-city { border-left: 3px solid #4ade80; }
.card-val {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.7rem;
  font-weight: 700;
  color: #fff;
  line-height: 1;
  display: block;
}
.card-label {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  display: block;
  margin-top: 4px;
}

/* ── SECTION HEADER ── */
.sec-header {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.8rem;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sec-header::after { content: none; }

/* ── STORY / AI BOX ── */
.ai-box {
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 0 12px 12px 0;
  padding: 1.2rem 1.4rem;
  font-size: 0.96rem;
  line-height: 1.8;
  color: var(--text);
  margin-top: 1rem;
}
.ai-box-label {
  font-size: 0.62rem;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.6rem;
  display: block;
}

/* ── DIVIDER ── */
.divider { height: 1px; margin: 1.2rem 0; background: var(--border); border: none; }

/* ── CLICK HINT ── */
.click-hint {
  font-size: 0.78rem;
  color: var(--muted);
  text-align: center;
  padding: 0.5rem;
  background: var(--bg2);
  border: 1px dashed var(--border);
  border-radius: 8px;
  margin-bottom: 0.8rem;
}

/* ══════════════════════════════════════════════
   COMPREHENSIVE TEXT VISIBILITY OVERRIDES
   Ensures ALL Streamlit native text is visible
   on the dark background theme.
══════════════════════════════════════════════ */

/* Caption */
div[data-testid="stCaptionContainer"],
div[data-testid="stCaptionContainer"] p,
div[data-testid="stCaptionContainer"] span,
.stCaption, .stCaption p { color: var(--muted) !important; }

/* All markdown containers — paragraphs, lists, spans */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] ul,
[data-testid="stMarkdownContainer"] ol,
[data-testid="stMarkdownContainer"] a,
.stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li {
  color: var(--text) !important;
}
/* Bold / strong */
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] b,
.stMarkdown strong, .stMarkdown b {
  color: #ffffff !important;
  font-weight: 600 !important;
}
/* Headings inside markdown */
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
  color: #ffffff !important;
}
/* Inline code */
[data-testid="stMarkdownContainer"] code {
  color: var(--accent) !important;
  background: rgba(74,222,128,0.08) !important;
  border-radius: 4px !important;
}

/* Widget labels (selectbox, slider, text input, toggle, radio, etc.) */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
label[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"],
[data-testid="stToggle"] label,
[data-testid="stCheckbox"] label,
[data-testid="stRadio"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSlider"] label,
[data-testid="stSlider"] p,
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small {
  color: var(--muted) !important;
}

/* Slider tick marks */
[data-testid="stTickBarMin"],
[data-testid="stTickBarMax"] { color: var(--muted) !important; }

/* Alert boxes text */
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div { color: var(--text) !important; }

/* Metric */
[data-testid="stMetricLabel"] p { color: var(--muted) !important; }
[data-testid="stMetricValue"]   { color: #ffffff !important; }
[data-testid="stMetricDelta"]   { color: var(--accent) !important; }

/* Headings */
h1, h2, h3, h4, h5, h6,
.stSubheader { color: #ffffff !important; }

/* Toggle / checkbox text */
[data-testid="stToggle"] p,
[data-testid="stCheckbox"] p { color: var(--text) !important; }

/* Expander header */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p { color: var(--text) !important; }

/* Download / generic button text already handled above */
/* Info / success / warning captions inside alert */
.stSuccess p, .stWarning p, .stInfo p, .stError p { color: var(--text) !important; }

.stSuccess { background: rgba(74,222,128,.07) !important; border: 1px solid rgba(74,222,128,.25) !important; border-radius: 8px !important; }
.stWarning { background: rgba(245,158,11,.07) !important; border: 1px solid rgba(245,158,11,.25) !important; border-radius: 8px !important; }
.stError   { background: rgba(239,68,68,.07)  !important; border: 1px solid rgba(239,68,68,.25)  !important; border-radius: 8px !important; }
.stInfo    { background: rgba(96,165,250,.07) !important; border: 1px solid rgba(96,165,250,.25) !important; border-radius: 8px !important; }
.stDownloadButton > button {
  font-size: 0.8rem !important;
  border-radius: 8px !important;
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--muted) !important;
}
.stDownloadButton > button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
</style>
"""

def setup_session_state(st):
    defaults = {
        "mode": "normal",
        "ds": None,
        "story_text": "",
        "sel_event": "2022 India Heatwave",
        "clicked_lat": None,
        "clicked_lon": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
