import streamlit as st
import pandas as pd
import tempfile
import xarray as xr

from src.config import CSS, setup_session_state
from src.data import load_sample
from src.pages.heatmap import render_heatmap
from src.pages.compare import render_compare
from src.pages.globe import render_globe
from src.pages.story import render_story
from src.pages.future_scope import render_future_scope

st.set_page_config(
    page_title="PyClimaExplorer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(CSS, unsafe_allow_html=True)
setup_session_state(st)

# ─── HERO ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-title">Py<span>Clima</span>Explorer</div>
  <div class="hero-sub">An interactive web dashboard for exploring 30+ years of global climate data — built for researchers and the curious alike.</div>
</div>
""", unsafe_allow_html=True)

# ─── DATA SOURCE ───────────────────────────────────────────────────────────────
st.markdown('<div class="sec-header">🌍 Data Source</div>', unsafe_allow_html=True)
st.markdown("""
<div class="card" style="padding: 1.5rem; margin-bottom: 1.5rem;">
""", unsafe_allow_html=True)

ds_col1, ds_col2 = st.columns([1, 1])

def _is_cdl_text(file_bytes):
    try:
        start = file_bytes[:300].decode("utf-8", errors="ignore").strip()
        return start.startswith("netcdf ") and "{" in start
    except Exception:
        return False

def _normalise_ds(raw_ds):
    import numpy as np
    import pandas as pd
    import xarray as xr

    ds = raw_ds.copy()
    info_msgs = []

    # 1. Normalise coordinate names
    coord_aliases = {
        "latitude":  ["lat", "LAT", "LATITUDE", "nav_lat", "y", "rlat", "nlat"],
        "longitude": ["lon", "LON", "LONGITUDE", "nav_lon", "x", "rlon", "nlon"],
        "time":      ["TIME", "t", "date", "DATE", "valid_time"],
    }
    rename_map = {}
    all_dc = set(list(ds.coords) + list(ds.dims))
    for target, aliases in coord_aliases.items():
        if target not in all_dc:
            for alias in aliases:
                if alias in all_dc:
                    rename_map[alias] = target
                    info_msgs.append(f"`{alias}` renamed to `{target}`")
                    break
    if rename_map:
        ds = ds.rename(rename_map)
    all_dc = set(list(ds.coords) + list(ds.dims))

    # 2. Handle spatial-only CESM/CVDP files (vars have only lat,lon dims, no time)
    lat_key = "latitude" if "latitude" in all_dc else ("lat" if "lat" in all_dc else None)
    lon_key = "longitude" if "longitude" in all_dc else ("lon" if "lon" in all_dc else None)

    spatial_vars = []
    if lat_key and lon_key:
        spatial_vars = [v for v in ds.data_vars
                        if set(ds[v].dims) == {lat_key, lon_key}]

    has_time_vars = any("time" in ds[v].dims for v in ds.data_vars)

    if not has_time_vars and spatial_vars:
        # Build synthetic annual time axis from TIME dim or default
        if "TIME" in all_dc:
            try:
                t_raw = ds["TIME"].values
                n_t = len(t_raw)
                start_yr = max(1, int(float(t_raw[0]))) if n_t > 0 else 1900
                start_yr = start_yr if 1800 <= start_yr <= 2200 else 1900
                times_synth = pd.date_range(f"{start_yr}-01-01", periods=n_t, freq="YS")
            except Exception:
                times_synth = pd.date_range("1900-01-01", periods=1, freq="YS")
        elif "time" in all_dc:
            try:
                t_raw = ds["time"].values
                n_t = len(t_raw)
                first_v = float(t_raw[0]) if n_t > 0 else 1900
                if 1800 <= first_v <= 2200:
                    try:
                        pd.to_datetime(t_raw)
                        times_synth = pd.DatetimeIndex(t_raw)
                    except Exception:
                        times_synth = pd.date_range(f"{int(first_v)}-01-01", periods=n_t, freq="YS")
                else:
                    times_synth = pd.date_range("1900-01-01", periods=n_t, freq="YS")
            except Exception:
                times_synth = pd.date_range("1900-01-01", periods=1, freq="YS")
        else:
            times_synth = pd.date_range("1900-01-01", periods=1, freq="YS")

        n_t = len(times_synth)
        lat_v = ds[lat_key].values
        lon_v = ds[lon_key].values

        # Find best temperature and precip spatial vars
        temp_kw = ["tas_spatialmean", "sst_spatialmean", "tas_trends", "sst_trends",
                   "tas", "sst", "temp", "t2m"]
        prec_kw = ["pr_spatialmean", "pr_trends", "precip", "rain", "pr_"]

        chosen_t = next((v for kw in temp_kw for v in spatial_vars if kw in v), None)
        chosen_p = next((v for kw in prec_kw for v in spatial_vars if kw in v), None)

        new_vars = {}
        if chosen_t:
            arr = ds[chosen_t].values.astype(np.float32)
            arr = np.where(arr < -800, np.nan, arr)
            arr3d = np.stack([arr] * n_t, axis=0)
            mean_v = float(np.nanmean(arr3d))
            if mean_v < 100:
                arr3d = arr3d + 273.15
                info_msgs.append(f"`{chosen_t}` (°C) converted to K")
            else:
                info_msgs.append(f"Using `{chosen_t}` as t2m")
            new_vars["t2m"] = xr.DataArray(arr3d,
                dims=["time","latitude","longitude"],
                coords={"time": times_synth, "latitude": lat_v, "longitude": lon_v},
                attrs={"units": "K", "long_name": f"Temperature from {chosen_t}"})

        if chosen_p:
            arr_p = ds[chosen_p].values.astype(np.float32)
            arr_p = np.where(arr_p < -800, np.nan, arr_p)
            arr_p3d = np.stack([arr_p] * n_t, axis=0) * 1e-3
            info_msgs.append(f"Using `{chosen_p}` as tp")
            new_vars["tp"] = xr.DataArray(arr_p3d,
                dims=["time","latitude","longitude"],
                coords={"time": times_synth, "latitude": lat_v, "longitude": lon_v},
                attrs={"units": "m", "long_name": f"Precipitation from {chosen_p}"})

        if new_vars:
            ds = xr.Dataset(new_vars,
                            coords={"time": times_synth, "latitude": lat_v, "longitude": lon_v})
            info_msgs.append("Restructured spatial fields into time-series format")

    # 3. Rename common variable aliases
    var_aliases_t2m = ["T2M","temperature","temp","air_temperature","tas","TAS",
                       "2m_temperature","t2","T2","air","TEMP","Temperature"]
    var_aliases_tp  = ["TP","precipitation","precip","pr","PR",
                       "total_precipitation","rain","RAIN","prcp","PRCP"]
    existing_vars = list(ds.data_vars)
    var_rename = {}
    if "t2m" not in existing_vars:
        for alias in var_aliases_t2m:
            if alias in existing_vars:
                var_rename[alias] = "t2m"
                info_msgs.append(f"`{alias}` renamed to `t2m`")
                break
    if "tp" not in existing_vars:
        for alias in var_aliases_tp:
            if alias in existing_vars:
                var_rename[alias] = "tp"
                info_msgs.append(f"`{alias}` renamed to `tp`")
                break
    if var_rename:
        ds = ds.rename(var_rename)

    # 4. Validate required coords
    all_dc2 = set(list(ds.coords) + list(ds.dims))
    missing = [c for c in ["latitude","longitude","time"] if c not in all_dc2]
    if missing:
        avail = ", ".join(sorted(set(list(raw_ds.coords)+list(raw_ds.dims))))
        return None, None, (
            f"❌ Could not find required coordinates: **{', '.join(missing)}**\n\n"
            f"Your file has: `{avail}`\n\n"
            "Please rename them to `latitude`, `longitude`, `time`."
        )

    # 5. Validate at least one usable variable
    if not any(v in ds.data_vars for v in ["t2m","tp"]):
        avail = ", ".join(list(ds.data_vars)[:20])
        return None, None, (
            f"❌ No usable variable found.\n\nYour file contains: `{avail}`\n\n"
            "The app needs variables with **3 dimensions (time × lat × lon)**. "
            "This file may be a diagnostics/statistics output — not a raw climate field file."
        )

    # 6. Ensure temperature in Kelvin
    if "t2m" in ds.data_vars:
        t_mean = float(ds["t2m"].mean())
        if t_mean < 150:
            ds["t2m"] = ds["t2m"] + 273.15
            info_msgs.append("Temperature converted from °C to K")

    info = " · ".join(info_msgs) if info_msgs else None
    return ds, info, None


with ds_col1:
    use_sample = st.toggle("Use built-in ERA5 sample (1990–2022)", value=True)
    if use_sample:
        with st.spinner("Loading ERA5 dataset…"):
            loaded_ds = load_sample()
        st.session_state.ds = loaded_ds
        st.success("ERA5 sample loaded  ✓")
    else:
        st.markdown("""
        <div style="font-size:0.78rem; color:#94a3b8; margin-bottom:0.6rem; line-height:1.6;">
          Upload any ERA5 or climate <b>.nc</b> file. Auto-detects variable and coordinate names.<br>
          Needs a temperature/precipitation variable on a lat×lon grid. ERA5, CMIP6, CESM supported.
        </div>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload a NetCDF file (.nc)",
            type=["nc"],
            help="ERA5, CMIP6, CESM, or any NetCDF with temperature/precipitation on a lat×lon grid.",
        )
        if uploaded_file:
            file_bytes = uploaded_file.read()
            if _is_cdl_text(file_bytes):
                st.error("❌ This is a **CDL text header file**, not a real NetCDF data file.")
                st.markdown("""
                <div style="font-size:0.8rem; color:#94a3b8; margin-top:0.5rem; line-height:1.7;">
                  A CDL file (starting with <code>netcdf ... {</code>) describes a dataset's structure
                  but contains <b>no actual data values</b>.<br><br>
                  <b>To get the real data file:</b><br>
                   • Download the full <code>.nc</code> binary from your data source (NCAR, Copernicus, CMIP archive)<br>
                   • If you have the CDL, generate NetCDF with: <code>ncgen -o output.nc header.cdl</code><br>
                   • For ERA5: download via <a href="https://cds.climate.copernicus.eu" style="color:#4ade80">Copernicus CDS</a>
                </div>
                """, unsafe_allow_html=True)
                st.session_state.ds = None
            else:
                with st.spinner(f"Reading {uploaded_file.name}…"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".nc") as tmp:
                        tmp.write(file_bytes)
                        tmp_path = tmp.name
                    try:
                        try:
                            raw_ds = xr.open_dataset(tmp_path, engine="netcdf4")
                        except Exception:
                            try:
                                raw_ds = xr.open_dataset(tmp_path, engine="scipy")
                            except Exception:
                                raw_ds = xr.open_dataset(tmp_path)
                        norm_ds, info_msg, err_msg = _normalise_ds(raw_ds)
                        if err_msg:
                            st.error(err_msg)
                            raw_dims = ", ".join(list(raw_ds.dims))
                            raw_vars = ", ".join(list(raw_ds.data_vars)[:15])
                            st.caption(f"File dims: `{raw_dims}` · Variables (first 15): `{raw_vars}`")
                            st.session_state.ds = None
                        else:
                            st.session_state.ds = norm_ds
                            st.success(f"✓ Loaded: **{uploaded_file.name}**")
                            if info_msg:
                                st.info(f"ℹ️ Auto-adjustments: {info_msg}")
                    except Exception as err:
                        st.error(f"❌ Failed to open file: {err}")
                        st.markdown("""
                        <div style="font-size:0.78rem;color:#94a3b8;margin-top:0.4rem;line-height:1.6;">
                          Make sure the file is a valid binary NetCDF4 (.nc) file.<br>
                          If it's NetCDF3 format, try: <code>nccopy -k nc4 input.nc output.nc</code>
                        </div>
                        """, unsafe_allow_html=True)
                        st.session_state.ds = None
        else:
            st.session_state.ds = None

with ds_col2:
    if st.session_state.ds is not None:
        _ds = st.session_state.ds
        st.markdown("**Dataset Info**")
        try:
            time_start = str(_ds.time.values[0])[:7]
            time_end   = str(_ds.time.values[-1])[:7]
            n_lat = len(_ds.latitude)
            n_lon = len(_ds.longitude)
            vars_str = ' · '.join(list(_ds.data_vars))
            st.caption(f"Variables: {vars_str} | Time: {time_start} → {time_end} | Grid: {n_lat} lat × {n_lon} lon")
        except Exception:
            st.caption(f"Variables: {', '.join(list(_ds.data_vars))}")
        st.markdown("**How to use the App**")
        st.caption("🗺️ Complete tabs below to explore heatmaps, compare eras, view 3D globes, read AI stories, or project the future with ML.")

st.markdown("</div>", unsafe_allow_html=True)

ds = st.session_state.ds
if ds is None:
    st.info("👆  Upload a NetCDF file or enable the ERA5 sample toggle to get started.")
    st.stop()

# ─── MODE BUTTONS ──────────────────────────────────────────────────────────────
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mode_defs = [
    ("normal",  "🗺️ Heatmap"),
    ("compare", "⚖️ Compare"),
    ("globe",   "🌐 Globe"),
    ("story",   "📖 Story"),
    ("future",  "🔮 Forecast"),
]

for col, (mkey, mlabel) in zip([mc1, mc2, mc3, mc4, mc5], mode_defs):
    with col:
        btype = "primary" if st.session_state.mode == mkey else "secondary"
        if st.button(mlabel, key=f"mode_{mkey}", type=btype, use_container_width=True):
            st.session_state.mode = mkey
            st.session_state.clicked_lat = None
            st.session_state.clicked_lon = None
            st.rerun()

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

VAR_LABELS = {"t2m": "2m Temperature", "tp": "Total Precipitation"}
times = pd.to_datetime(ds.time.values)

var_col, _ = st.columns([2, 4])
with var_col:
    sel_var = st.selectbox("Variable", list(ds.data_vars),
                           format_func=lambda x: VAR_LABELS.get(x, x))

# ─── ROUTER ────────────────────────────────────────────────────────────────────
if st.session_state.mode == "normal":
    render_heatmap(ds, times, sel_var, VAR_LABELS)
elif st.session_state.mode == "compare":
    render_compare(ds, times, sel_var)
elif st.session_state.mode == "globe":
    render_globe(ds, times, sel_var, VAR_LABELS)
elif st.session_state.mode == "story":
    render_story(ds, times)
elif st.session_state.mode == "future":
    render_future_scope(ds, times, sel_var, VAR_LABELS)


