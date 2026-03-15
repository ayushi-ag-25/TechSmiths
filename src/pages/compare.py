import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from src.utils import to_celsius, nearest_idx, do_geocode
from src.plotting import make_heatmap, make_timeseries, clean_layout

def render_compare(ds, times, sel_var):
    st.markdown('<div class="sec-header">⚖️ Side-by-Side Year Comparison</div>', unsafe_allow_html=True)
    st.caption("Compare climate conditions between two different months/years. Both maps use the same colour scale so colours are directly comparable.")

    cmp_col1, cmp_col2 = st.columns(2)
    with cmp_col1:
        st.markdown("**Year A — Baseline**")
        st.markdown("**Time Slider A**")
        idx_a = st.slider("", 0, len(times)-1, 0, key="slider_a", label_visibility="collapsed")
        st.caption(f"📅 {str(times[idx_a])[:7]}")
    with cmp_col2:
        st.markdown("**Year B — Comparison**")
        st.markdown("**Time Slider B**")
        idx_b = st.slider("", 0, len(times)-1, min(len(times)-1, 360), key="slider_b", label_visibility="collapsed")
        st.caption(f"📅 {str(times[idx_b])[:7]}")

    da_a = ds[sel_var].isel(time=idx_a)
    da_b = ds[sel_var].isel(time=idx_b)
    if sel_var == "t2m":
        da_a, da_b = to_celsius(da_a), to_celsius(da_b)
    else:
        da_a, da_b = da_a * 1000, da_b * 1000

    zmin = float(min(da_a.min(), da_b.min()))
    zmax = float(max(da_a.max(), da_b.max()))

    map_a, map_b = st.columns(2)
    with map_a:
        fig_a = make_heatmap(ds, sel_var, idx_a,
                              title=f"Baseline · {str(times[idx_a])[:7]}",
                              zmin=zmin, zmax=zmax, height=380)
        fig_a.update_layout(
            title=dict(text=f"◼ Baseline · {str(times[idx_a])[:7]}",
                       font=dict(color="#60a5fa", size=12), x=0.01)
        )
        sel_a = st.plotly_chart(fig_a, use_container_width=True, key="compare_map_a", on_select="rerun", selection_mode="points")
        mean_a = float(da_a.mean())
        unit_c = "°C" if sel_var == "t2m" else "mm"
        st.markdown(f'<div class="card"><span class="card-val" style="color:#60a5fa">{mean_a:.1f} {unit_c}</span><span class="card-label">Global mean — Baseline</span></div>', unsafe_allow_html=True)

    with map_b:
        fig_b = make_heatmap(ds, sel_var, idx_b,
                              title=f"Comparison · {str(times[idx_b])[:7]}",
                              zmin=zmin, zmax=zmax, height=380)
        fig_b.update_layout(
            title=dict(text=f"◼ Comparison · {str(times[idx_b])[:7]}",
                       font=dict(color="#f97316", size=12), x=0.01)
        )
        sel_b = st.plotly_chart(fig_b, use_container_width=True, key="compare_map_b", on_select="rerun", selection_mode="points")
        mean_b = float(da_b.mean())
        delta  = mean_b - mean_a
        d_col  = "#ef4444" if delta > 0 else "#4ade80"
        st.markdown(f'<div class="card"><span class="card-val" style="color:{d_col}">{mean_b:.1f} {unit_c}</span><span class="card-label">Global mean — Comparison</span></div>', unsafe_allow_html=True)
        
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    cmp_lat = cmp_lon = None
    if sel_a and sel_a.get("selection") and sel_a["selection"].get("points"):
        pt = sel_a["selection"]["points"][0]
        cmp_lat, cmp_lon = pt.get("lat"), pt.get("lon")
    elif sel_b and sel_b.get("selection") and sel_b["selection"].get("points"):
        pt = sel_b["selection"]["points"][0]
        cmp_lat, cmp_lon = pt.get("lat"), pt.get("lon")
        
    if cmp_lat is not None and cmp_lon is not None:
         li, lj = nearest_idx(ds, cmp_lat, cmp_lon)
         actual_lat = float(ds.latitude.values[li])
         actual_lon = float(ds.longitude.values[lj])
         st.markdown(f"### 📈 30-Year Trend at ({actual_lat:.1f}°, {actual_lon:.1f}°)")
         fig_ts = make_timeseries(ds, sel_var, li, lj, label=f"{actual_lat:.1f}°N, {actual_lon:.1f}°E")
         st.plotly_chart(fig_ts, use_container_width=True)
         st.caption(
             "📌 Thin line = monthly values · 🟡 Thick gold line = 12-month average (removes seasonal noise) · "
             "🔴 Dotted red = long-term climate trend · ▲ / ▼ = record high / low."
         )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("**City time-series comparison**")
    city_cmp = st.text_input("Enter a city to compare across both periods", placeholder="Delhi, Paris, New York…", key="city_cmp")
    if city_cmp:
        lat_c, lon_c = do_geocode(city_cmp)
        if lat_c is not None:
            li, lj = nearest_idx(ds, lat_c, lon_c)
            da_city = ds[sel_var].isel(latitude=li, longitude=lj)
            if sel_var == "t2m":
                da_city = to_celsius(da_city)
            else:
                da_city = da_city * 1000
            mid = len(times) // 2
            unit_cmp = "°C" if sel_var == "t2m" else "mm"
            var_name_cmp = "Temperature" if sel_var == "t2m" else "Precipitation"

            s1 = pd.Series(da_city.values[:mid], index=pd.to_datetime(ds.time.values[:mid]))
            s2 = pd.Series(da_city.values[mid:], index=pd.to_datetime(ds.time.values[mid:]))
            roll1 = s1.rolling(12, center=True, min_periods=6).mean()
            roll2 = s2.rolling(12, center=True, min_periods=6).mean()

            x1 = np.arange(len(s1), dtype=float)
            x2 = np.arange(len(s2), dtype=float)
            slope1 = np.polyfit(x1, s1.values, 1)[0] * 120
            slope2 = np.polyfit(x2, s2.values, 1)[0] * 120

            mean1 = float(s1.mean())
            mean2 = float(s2.mean())
            delta_mean = mean2 - mean1
            delta_color = "#ef4444" if delta_mean > 0 else "#4ade80"
            delta_sign = "+" if delta_mean >= 0 else ""

            fig_dual = go.Figure()
            fig_dual.add_trace(go.Scatter(
                x=pd.to_datetime(ds.time.values[:mid]), y=da_city.values[:mid],
                mode="lines", line=dict(color="#60a5fa", width=1.5),
                fill="tozeroy", fillcolor="rgba(96,165,250,0.06)",
                name=f"1990–2007 Monthly",
                hovertemplate="<b>%{x|%b %Y}</b><br>" + f"{var_name_cmp}: <b>%{{y:.1f}} {unit_cmp}</b><extra></extra>",
                opacity=0.7,
            ))
            fig_dual.add_trace(go.Scatter(
                x=pd.to_datetime(ds.time.values[:mid]), y=roll1.values,
                mode="lines", line=dict(color="#93c5fd", width=2.5),
                name=f"1990–2007 Avg  (mean {mean1:.1f}{unit_cmp}, trend {'+' if slope1>=0 else ''}{slope1:.2f}{unit_cmp}/decade)",
                hovertemplate="<b>%{x|%b %Y}</b><br>12-Mo Avg: <b>%{y:.1f} " + unit_cmp + "</b><extra></extra>",
            ))
            fig_dual.add_trace(go.Scatter(
                x=pd.to_datetime(ds.time.values[mid:]), y=da_city.values[mid:],
                mode="lines", line=dict(color="#f97316", width=1.5),
                fill="tozeroy", fillcolor="rgba(249,115,22,0.06)",
                name=f"2008–2022 Monthly",
                hovertemplate="<b>%{x|%b %Y}</b><br>" + f"{var_name_cmp}: <b>%{{y:.1f}} {unit_cmp}</b><extra></extra>",
                opacity=0.7,
            ))
            fig_dual.add_trace(go.Scatter(
                x=pd.to_datetime(ds.time.values[mid:]), y=roll2.values,
                mode="lines", line=dict(color="#fdba74", width=2.5),
                name=f"2008–2022 Avg  (mean {mean2:.1f}{unit_cmp}, trend {'+' if slope2>=0 else ''}{slope2:.2f}{unit_cmp}/decade)",
                hovertemplate="<b>%{x|%b %Y}</b><br>12-Mo Avg: <b>%{y:.1f} " + unit_cmp + "</b><extra></extra>",
            ))
            fig_dual.update_layout(
                height=380,
                xaxis_title="Year",
                yaxis_title=f"{var_name_cmp} ({unit_cmp})",
                title=dict(text=f"📊 {var_name_cmp} Comparison — {city_cmp}",
                           font=dict(size=13, color="#e2e8f0", weight=600), x=0.0),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(family="Inter", size=9), bgcolor="rgba(0,0,0,0)",
                ),
                **clean_layout(
                    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                               color="#94a3b8", showline=True, linecolor="rgba(255,255,255,0.08)",
                               tickformat="%Y", dtick="M24"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                               color="#94a3b8", showline=True, linecolor="rgba(255,255,255,0.08)",
                               zeroline=True, zerolinecolor="rgba(255,255,255,0.12)", zerolinewidth=1),
                )
            )
            st.plotly_chart(fig_dual, use_container_width=True)
            st.caption(
                f"🔵 Blue = early period (1990–2007) · 🟠 Orange = recent period (2008–2022) · "
                f"Thick lines = 12-month rolling average  |  "
                f"Change in mean: **{delta_sign}{delta_mean:.2f} {unit_cmp}** compared to baseline."
            )
        else:
            st.warning("City not found. Try a different spelling.")
