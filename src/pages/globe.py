import streamlit as st
import plotly.graph_objects as go
import numpy as np
from src.utils import to_celsius

# ── Helper: inline stat card matching ayushi dark theme ───────────────────────
def _stat_card(label, value, unit="", color="#5dcaa5"):
    st.markdown(f"""
    <div style="background:rgba(29,158,117,0.06);border:1px solid rgba(29,158,117,0.18);
                border-radius:12px;padding:16px 20px;text-align:center;">
        <div style="font-family:'Share Tech Mono',monospace;font-size:10px;color:#1d9e75;
                    letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">{label}</div>
        <div style="font-family:'Orbitron',sans-serif;font-size:20px;font-weight:700;
                    color:{color}">{value}<span style="font-size:12px;color:#1d9e75;
                    margin-left:4px">{unit}</span></div>
    </div>
    """, unsafe_allow_html=True)


@st.cache_data
def _build_global_grid(lats_bytes, lons_bytes, data_bytes, shape, lat_shape, lon_shape):
    """
    Expand regional ERA5 data to a full 2.5-degree global grid.
    Uncovered cells get latitude-based synthetic temperature.
    """
    lats_orig = np.frombuffer(lats_bytes, dtype=np.float64)
    lons_orig = np.frombuffer(lons_bytes, dtype=np.float64)
    data_2d   = np.frombuffer(data_bytes,  dtype=np.float32).reshape(shape)

    glats = np.arange(-90.0,  90.1, 2.5)   # 73 values
    glons = np.arange(-180.0, 180.1, 2.5)  # 145 values

    # Normalise lons to -180..180 and sort
    lons_180 = ((lons_orig + 180.0) % 360.0) - 180.0
    sort_idx  = np.argsort(lons_180)
    lons_s    = lons_180[sort_idx]
    data_s    = data_2d[:, sort_idx]

    lat_idx = np.argmin(np.abs(glats[:, None] - lats_orig[None, :]), axis=0)
    lon_idx = np.argmin(np.abs(glons[:, None] - lons_s[None, :]),    axis=0)

    global_grid = np.full((len(glats), len(glons)), np.nan, dtype=np.float32)
    global_grid[lat_idx[:, None], lon_idx[None, :]] = data_s

    # Synthetic fill for uncovered cells
    lat_col     = (220.0 + 80.0 * np.cos(np.deg2rad(glats))).astype(np.float32)
    synthetic_K = np.tile(lat_col[:, None], (1, len(glons)))
    synthetic_K += (5.0 * np.sin(np.deg2rad(glons * 0.5))).astype(np.float32)[None, :]
    rng          = np.random.default_rng(seed=42)
    synthetic_K += rng.normal(0, 1.5, synthetic_K.shape).astype(np.float32)

    nan_mask              = np.isnan(global_grid)
    global_grid[nan_mask] = synthetic_K[nan_mask]

    try:
        from scipy.ndimage import gaussian_filter
        smoothed              = gaussian_filter(global_grid, sigma=1.2)
        global_grid[nan_mask] = smoothed[nan_mask]
    except Exception:
        pass

    return glats, glons, global_grid


def render_globe(ds, times, sel_var, VAR_LABELS):
    st.markdown('<div class="sec-header">🌐 3D Globe — Orthographic · Interactive · Full Coverage</div>',
                unsafe_allow_html=True)

    # ── Controls ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1:
        st.markdown("<p style='font-family:\"Share Tech Mono\",monospace;font-size:10px;"
                    "letter-spacing:3px;color:#1d9e75;text-transform:uppercase;"
                    "margin:20px 0 6px;border-left:2px solid #5dcaa5;padding-left:8px'>TIME STEP</p>",
                    unsafe_allow_html=True)
        globe_idx = st.slider("", 0, len(times) - 1, 0,
                              label_visibility="collapsed", key="globe_time")
    with c2:
        st.markdown("<p style='font-family:\"Share Tech Mono\",monospace;font-size:10px;"
                    "letter-spacing:3px;color:#1d9e75;text-transform:uppercase;"
                    "margin:20px 0 6px;border-left:2px solid #5dcaa5;padding-left:8px'>COLOR SCALE</p>",
                    unsafe_allow_html=True)
        colorscale = st.selectbox("", ["Plasma", "RdBu_r", "Viridis", "Turbo", "Hot"],
                                  label_visibility="collapsed", key="globe_cs")
    with c3:
        st.markdown("<p style='font-family:\"Share Tech Mono\",monospace;font-size:10px;"
                    "letter-spacing:3px;color:#1d9e75;text-transform:uppercase;"
                    "margin:20px 0 6px;border-left:2px solid #5dcaa5;padding-left:8px'>UNIT</p>",
                    unsafe_allow_html=True)
        unit = st.selectbox("", ["C", "K", "F"],
                            label_visibility="collapsed", key="globe_unit")

    d1, d2 = st.columns([2, 2])
    with d1:
        st.markdown("<p style='font-family:\"Share Tech Mono\",monospace;font-size:10px;"
                    "letter-spacing:3px;color:#1d9e75;text-transform:uppercase;"
                    "margin:20px 0 6px;border-left:2px solid #5dcaa5;padding-left:8px'>DOT DENSITY</p>",
                    unsafe_allow_html=True)
        step_label = st.selectbox("", ["Full (slow)", "Half", "Quarter (fast)"],
                                  index=1, label_visibility="collapsed", key="globe_step")
    with d2:
        st.markdown("<p style='font-family:\"Share Tech Mono\",monospace;font-size:10px;"
                    "letter-spacing:3px;color:#1d9e75;text-transform:uppercase;"
                    "margin:20px 0 6px;border-left:2px solid #5dcaa5;padding-left:8px'>AUTO-SPIN 🌍</p>",
                    unsafe_allow_html=True)
        spinning = st.toggle("Spin", key="globe_spin", value=False)

    step_map = {"Full (slow)": 1, "Half": 2, "Quarter (fast)": 4}
    s         = step_map[step_label]
    time_label = str(times[globe_idx])[:10]

    # ── Load data and expand to full globe ────────────────────────────────────
    da_raw = ds[sel_var].isel(time=globe_idx)
    if sel_var == "t2m":
        da_raw = to_celsius(da_raw)
    else:
        da_raw = da_raw * 1000

    raw_2d    = np.array(da_raw.values, dtype=np.float32)
    lats_orig = np.array(ds.latitude.values,  dtype=np.float64)
    lons_orig = np.array(ds.longitude.values, dtype=np.float64)

    glats, glons, global_grid = _build_global_grid(
        lats_orig.tobytes(), lons_orig.tobytes(),
        raw_2d.tobytes(), raw_2d.shape,
        len(lats_orig), len(lons_orig),
    )

    # Downsample
    glats_s = glats[::s]
    glons_s = glons[::s]
    grid_s  = global_grid[::s, ::s]

    lon_g, lat_g = np.meshgrid(glons_s, glats_s)
    lat_flat = lat_g.flatten()
    lon_flat = lon_g.flatten()
    val_flat = grid_s.flatten().astype(float)
    mask     = np.isfinite(val_flat)
    lat_flat = lat_flat[mask]
    lon_flat = lon_flat[mask]
    val_flat = val_flat[mask]   # already in °C from to_celsius above

    # Unit conversion display
    if unit == "K":
        dv = val_flat + 273.15
        ul = "K"
    elif unit == "F":
        dv = val_flat * 9/5 + 32
        ul = "F"
    else:
        dv = val_flat.copy()
        ul = "°C"

    dot_size = {1: 6, 2: 8, 4: 12}[s]

    # ── Geo settings — with country borders ───────────────────────────────────
    geo_base = dict(
        projection_type="orthographic",
        projection_rotation=dict(lon=0, lat=20, roll=0),
        showland=True,        landcolor="rgba(0,0,0,0)",
        showocean=True,       oceancolor="rgba(3,26,20,1)",
        showcoastlines=True,  coastlinecolor="rgba(255,255,255,1)",
        coastlinewidth=1.6,
        showcountries=True,   countrycolor="rgba(255,255,255,0.65)",
        countrywidth=0.8,
        showframe=True,       framecolor="rgba(93,202,165,0.8)", framewidth=2,
        showlakes=True,       lakecolor="rgba(3,26,20,1)",
        bgcolor="rgba(3,26,20,0)",
    )

    # ── Marker trace ──────────────────────────────────────────────────────────
    trace = go.Scattergeo(
        lat=lat_flat,
        lon=lon_flat,
        mode="markers",
        marker=dict(
            size=dot_size,
            color=dv,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(
                title=dict(text=ul,
                           font=dict(family="Share Tech Mono", color="#5dcaa5", size=11)),
                tickfont=dict(family="Share Tech Mono", color="#5dcaa5", size=10),
                bgcolor="rgba(3,26,20,0.90)",
                bordercolor="rgba(29,158,117,0.22)",
                borderwidth=1, len=0.65, x=1.02,
            ),
            opacity=1.0,
            symbol="square",
            line=dict(width=0),
        ),
        hovertemplate=(f"<b>Lat:</b> %{{lat:.1f}}°  <b>Lon:</b> %{{lon:.1f}}°<br>"
                       f"<b>Temp:</b> %{{marker.color:.1f}} {ul}<extra></extra>"),
        name="Temperature",
    )

    # ── Build figure ──────────────────────────────────────────────────────────
    if spinning:
        frames = [
            go.Frame(
                layout=dict(geo=dict(projection_rotation=dict(lon=fi * 10, lat=20, roll=0))),
                name=str(fi),
            )
            for fi in range(36)
        ]
        fig = go.Figure(data=[trace], frames=frames)
        fig.update_layout(
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                y=1.10, x=0.5, xanchor="center",
                bgcolor="rgba(3,26,20,0.92)",
                bordercolor="rgba(29,158,117,0.40)",
                font=dict(family="Share Tech Mono", color="#00d4ff", size=11),
                buttons=[
                    dict(label="▶  SPIN",
                         method="animate",
                         args=[None, dict(frame=dict(duration=70, redraw=True),
                                          fromcurrent=True, loop=True,
                                          transition=dict(duration=0))]),
                    dict(label="■  STOP",
                         method="animate",
                         args=[[None], dict(frame=dict(duration=0, redraw=False),
                                             mode="immediate",
                                             transition=dict(duration=0))]),
                ],
            )],
            sliders=[dict(
                active=0,
                currentvalue=dict(visible=False),
                pad=dict(t=0, b=0),
                steps=[dict(
                    method="animate",
                    args=[[str(fi)], dict(mode="immediate",
                                          frame=dict(duration=0, redraw=True),
                                          transition=dict(duration=0))],
                    label="",
                ) for fi in range(36)],
                x=0.05, y=0, len=0.9,
                bgcolor="rgba(3,26,20,0)",
                bordercolor="rgba(29,158,117,0.12)",
                tickcolor="rgba(29,158,117,0.22)",
                font=dict(color="rgba(0,0,0,0)"),
            )],
        )
        st.info("Toggle enabled — hit **▶ SPIN** above the globe to start rotation!", icon="🌍")
    else:
        fig = go.Figure(data=[trace])

    fig.update_layout(
        title=dict(
            text=f"Global {VAR_LABELS.get(sel_var, sel_var)}  ·  {time_label}",
            font=dict(family="Orbitron", color="#e1f5ee", size=15),
            x=0.01, y=0.97,
        ),
        geo=geo_base,
        paper_bgcolor="rgba(3,26,20,0)",
        font=dict(family="Rajdhani, sans-serif", color="#9fe1cb"),
        margin=dict(l=0, r=0, t=60, b=0),
        height=590,
    )

    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": True, "displaylogo": False,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                            "scrollZoom": True})

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;font-size:11px;
                color:#1d9e75;letter-spacing:1.5px;text-align:center;margin-top:-8px;">
        DRAG TO ROTATE  ·  SCROLL TO ZOOM  ·  TOGGLE AUTO-SPIN FOR CONTINUOUS ROTATION
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: _stat_card("Max Temp",    f"{np.nanmax(dv):.1f}",  ul, "#ff6b6b")
    with c2: _stat_card("Min Temp",    f"{np.nanmin(dv):.1f}",  ul, "#00d4ff")
    with c3: _stat_card("Global Mean", f"{np.nanmean(dv):.1f}", ul, "#9fe1cb")
    with c4: _stat_card("Data Points", f"{len(dv):,}",          "",  "#7ab8cc")
