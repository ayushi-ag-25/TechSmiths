import streamlit as st
import numpy as np
import pandas as pd
import requests
import plotly.graph_objects as go
from src.utils import do_geocode, nearest_idx, to_celsius
from src.plotting import clean_layout, CLIM_CS

@st.cache_data(show_spinner=False)
def get_country_name(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"lat": lat, "lon": lon, "format": "json"}
        resp = requests.get(url, params=params, headers={"User-Agent": "pce_v3_reverse"}, timeout=2)
        if resp.ok:
            data = resp.json()
            addr = data.get("address", {})
            return addr.get("country", addr.get("state", "Ocean Area"))
    except:
        pass
    return "Ocean Area"

@st.cache_data(show_spinner=False)
def run_pixelwise_ml(_ds, sel_var, target_year, model_type):
    da = _ds[sel_var]
    if sel_var == "t2m":
        da = to_celsius(da)
    else:
        da = da * 1000

    vals = da.values
    times = pd.to_datetime(_ds.time.values)

    years_decimal = times.year + (times.dayofyear - 1) / 365.25
    x = years_decimal.values

    n_lat, n_lon = vals.shape[1], vals.shape[2]

    if model_type == "Polynomial (Degree 2)":
        x_matrix = np.vstack([x**2, x, np.ones(len(x))]).T
        pred_x = np.array([target_year**2, target_year, 1.0])
    else:
        x_matrix = np.vstack([x, np.ones(len(x))]).T
        pred_x = np.array([target_year, 1.0])

    y_flat = vals.reshape(len(x), -1)
    mask = ~np.isnan(y_flat[0])
    y_valid = y_flat[:, mask]

    w, _, _, _ = np.linalg.lstsq(x_matrix, y_valid, rcond=None)
    proj_valid = pred_x @ w

    hist_mean_valid = np.mean(y_valid, axis=0)
    mid_year = np.mean(x)
    rate_valid = (proj_valid - hist_mean_valid) / max(1.0, target_year - mid_year) * 10

    proj_flat = np.full(n_lat * n_lon, np.nan)
    rate_flat = np.full(n_lat * n_lon, np.nan)

    proj_flat[mask] = proj_valid
    rate_flat[mask] = rate_valid

    global_hist = np.nanmean(y_flat, axis=1)

    return proj_flat.reshape((n_lat, n_lon)), rate_flat.reshape((n_lat, n_lon)), x, global_hist

def plot_global_trend(x_hist, y_hist, target_year, model_type, unit_label):
    if model_type == "Polynomial (Degree 2)":
        coeffs = np.polyfit(x_hist, y_hist, 2)
    else:
        coeffs = np.polyfit(x_hist, y_hist, 1)

    x_proj = np.linspace(x_hist[-1], target_year, 50)
    y_proj = np.polyval(coeffs, x_proj)
    y_fit = np.polyval(coeffs, x_hist)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_hist, y=y_hist, mode="lines", line=dict(color="rgba(96, 165, 250, 0.4)", width=1.5), name="Historical"))
    fig.add_trace(go.Scatter(x=x_hist, y=y_fit, mode="lines", line=dict(color="#60a5fa", width=3), name="Model Fit"))
    fig.add_trace(go.Scatter(x=x_proj, y=y_proj, mode="lines", line=dict(color="#ef4444", width=3, dash="dot"), name="Projection"))
    fig.add_trace(go.Scatter(x=[target_year], y=[y_proj[-1]], mode="markers+text", marker=dict(size=10, color="#ef4444"), text=[f"{y_proj[-1]:.1f}{unit_label}"], textposition="top left", textfont=dict(color="#ef4444", size=11, family="Inter"), showlegend=False))
    fig.update_layout(height=180, title=dict(text="Global Avg Projection", font=dict(family="Inter", size=11, color="#94a3b8")), showlegend=False, **clean_layout(margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)"), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)")))
    return fig

def run_city_forecast(ds, sel_var, lat, lon):
    li, lj = nearest_idx(ds, lat, lon)
    da = ds[sel_var].isel(latitude=li, longitude=lj)
    unit = "°C" if sel_var == "t2m" else "mm"
    if sel_var == "t2m": da = to_celsius(da)
    else: da = da * 1000

    times = pd.to_datetime(ds.time.values)
    y_hist = da.values
    x_hist = times.year + (times.dayofyear - 1) / 365.25
    valid = ~np.isnan(y_hist)
    x_valid = x_hist[valid]
    y_valid = y_hist[valid]

    coeffs, cov = np.polyfit(x_valid, y_valid, 2, cov=True)
    x_proj = np.linspace(x_hist[-1], 2050.0, 100)
    y_fit = np.polyval(coeffs, x_valid)
    y_proj = np.polyval(coeffs, x_proj)

    residuals = y_valid - y_fit
    std_error = np.std(residuals)
    years_ahead = x_proj - x_hist[-1]
    expansion_factor = 1.0 + (years_ahead * 0.05)
    ci_bound = 1.96 * std_error * expansion_factor
    y_upper = y_proj + ci_bound
    y_lower = y_proj - ci_bound

    return times[valid], y_valid, x_proj, y_proj, y_upper, y_lower, unit, y_hist[-1], y_proj[-1]

def render_future_scope(ds, times, sel_var, VAR_LABELS):
    st.markdown('<div class="sec-header">🔮 Forecast Mode — Global & City Projections</div>', unsafe_allow_html=True)

    # --- PART 1: GLOBAL CONTINUOUS HEATMAP ---
    st.markdown("### 1. Global Climate Projection")
    st.caption("Use historical ERA5 data to extrapolate future global conditions.")

    fs_col1, fs_col2 = st.columns([3, 1])
    with fs_col2:
        model_type = "Polynomial (Degree 2)"
        target_year = st.slider("Target Year", min_value=2030, max_value=2100, value=2050, step=5)

        with st.spinner(f"Training {len(ds.latitude)*len(ds.longitude)} ML models globally..."):
            proj_grid, rates_grid, x_hist, global_hist = run_pixelwise_ml(ds, sel_var, target_year, model_type)

        unit_label = "°C" if sel_var == "t2m" else "mm"
        gmean = float(np.nanmean(proj_grid))

        da_hist = ds[sel_var]
        if sel_var == "t2m": da_hist = to_celsius(da_hist)
        else: da_hist = da_hist * 1000
        baseline_mean = float(da_hist.mean())

        delta = gmean - baseline_mean
        d_sign = "+" if delta >= 0 else ""
        d_color = "#ef4444" if delta > 0 else "#4ade80"

        st.markdown(f"""
        <div class="card card-max" style="border-left-color:{d_color}">
          <span class="card-val">{gmean:.1f}{unit_label}</span>
          <span class="card-label">Projected Global Average</span>
        </div>
        <div style="font-size:0.8rem; margin-top:-5px; margin-bottom:1rem; color:{d_color}; font-weight:600;">
          {d_sign}{delta:.2f}{unit_label} vs baseline
        </div>
        """, unsafe_allow_html=True)

        st.plotly_chart(plot_global_trend(x_hist, global_hist, target_year, model_type, unit_label), use_container_width=True)

        st.markdown("**🚨 Extreme Risk Regions**")
        flat_rates = rates_grid.flatten()
        valid_indices = np.where(~np.isnan(flat_rates))[0]
        if len(valid_indices) > 0:
            top_indices = valid_indices[np.argsort(flat_rates[valid_indices])[-3:]][::-1]
            for rank, idx in enumerate(top_indices):
                lat_idx = idx // len(ds.longitude)
                lon_idx = idx % len(ds.longitude)
                lat_val = float(ds.latitude.values[lat_idx])
                lon_val = float(ds.longitude.values[lon_idx])
                trend_val = flat_rates[idx]
                country_nm = get_country_name(lat_val, lon_val)
                st.markdown(f"""
                <div style="background:#1a1f2e; border:1px solid rgba(239,68,68,0.3); border-left:3px solid #ef4444; border-radius:8px; padding:0.6rem; margin-bottom:0.6rem;">
                  <div style="font-size:0.75rem; font-weight:600; color:#e2e8f0;">#{rank+1} {country_nm}</div>
                  <div style="font-size:0.7rem; color:#ef4444; margin-top:2px;">+{trend_val:.2f}{unit_label}/decade</div>
                </div>
                """, unsafe_allow_html=True)

    with fs_col1:
        lats = ds.latitude.values
        lons = ds.longitude.values
        lat_l, lon_l, z_l = [], [], []
        for i in range(len(lats)):
            for j in range(len(lons)):
                v = float(proj_grid[i, j])
                if not np.isnan(v):
                    lat_l.append(float(lats[i]))
                    lon_l.append(float(lons[j]))
                    z_l.append(v)

        vmin = float(np.nanmin(da_hist.values))
        vmax = float(np.nanmax(da_hist.values)) + (delta * 1.5)

        deg_spacing = abs(float(lats[1]) - float(lats[0])) if len(lats) > 1 else 2.5
        marker_size = max(4, round(deg_spacing * (700.0 / 360.0) * 1.35))

        fig_map = go.Figure()
        fig_map.add_trace(go.Scattergeo(
            lat=lat_l, lon=lon_l, mode="markers",
            marker=dict(
                symbol="square", color=z_l, colorscale=CLIM_CS, cmin=vmin, cmax=vmax,
                size=marker_size, opacity=0.95,
                colorbar=dict(title=dict(text=unit_label, font=dict(family="Inter", size=10, color="#94a3b8")),
                              thickness=12, len=0.7, tickfont=dict(family="Inter", size=10, color="#94a3b8"),
                              bgcolor="rgba(15,17,23,0.9)", bordercolor="rgba(255,255,255,0.1)", x=1.01),
                line=dict(width=0)
            ),
            hovertemplate="<b>%{lat:.1f}°, %{lon:.1f}°</b><br>Projected: <b>%{marker.color:.1f} " + unit_label + "</b><extra></extra>"
        ))
        geo_opts = dict(
            showland=True, landcolor="rgba(28,37,54,1.0)", showocean=True, oceancolor="rgba(10,15,25,1.0)",
            showlakes=True, lakecolor="rgba(12,20,35,1.0)", showcountries=True,
            countrycolor="rgba(255,255,255,0.75)", countrywidth=1.5,
            showcoastlines=True, coastlinecolor="rgba(255,255,255,0.85)", coastlinewidth=1.5,
            bgcolor="#0f1117", framecolor="rgba(255,255,255,0.2)", framewidth=1,
            lonaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", gridwidth=0.5),
            lataxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", gridwidth=0.5),
            projection_type="natural earth"
        )
        fig_map.update_layout(
            geo=geo_opts, height=500, margin=dict(l=0, r=40, t=30, b=0),
            title=dict(text=f"Continuous Global Forecast vs {target_year}", font=dict(family="Inter", size=12, color="#e2e8f0"), x=0.01),
            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", font=dict(family="Inter", color="#e2e8f0"),
            hoverlabel=dict(bgcolor="#181c27", bordercolor="rgba(74,222,128,0.4)", font=dict(family="Inter", size=11))
        )
        st.plotly_chart(fig_map, use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # --- PART 2: CITY FAN CHART ---
    st.markdown("### 2. City-Level 2050 Risk Assessment")
    st.caption("Extrapolate a city's historical pattern to 2050 using polynomial regression.")

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        if "forecast_city" not in st.session_state:
            st.session_state.forecast_city = ""
        city_input = st.text_input("Enter a City", placeholder="Miami, Jakarta, London...", key="fc_city", label_visibility="collapsed")
    with c2:
        fc_btn = st.button("▶ Run City Forecast", type="primary", use_container_width=True)

    if city_input and fc_btn:
        lat, lon = do_geocode(city_input)
        if lat is None:
            st.error("City not found. Please try a different spelling.")
        else:
            with st.spinner(f"Running Polynomial Regression for {city_input}..."):
                t_hist, y_hist, x_proj, y_proj, y_upper, y_lower, unit, hist_last, proj_2050 = run_city_forecast(ds, sel_var, lat, lon)

            delta_2050 = proj_2050 - hist_last
            d_sign = "+" if delta_2050 > 0 else ""
            d_color = "#ef4444" if delta_2050 > 0 else "#4ade80"
            var_name = "Temperature" if sel_var == "t2m" else "Precipitation"

            fig_city = go.Figure()
            fig_city.add_trace(go.Scatter(
                x=np.concatenate([x_proj, x_proj[::-1]]), y=np.concatenate([y_upper, y_lower[::-1]]),
                fill="toself", fillcolor="rgba(239, 68, 68, 0.15)" if delta_2050 > 0 else "rgba(74, 222, 128, 0.15)",
                line=dict(color="rgba(255,255,255,0)"), hoverinfo="skip", showlegend=True, name="95% Confidence Band"
            ))
            x_hist_dec = t_hist.year + (t_hist.dayofyear - 1)/365.25
            y_hist_smooth = pd.Series(y_hist).rolling(12, center=True, min_periods=1).mean()
            fig_city.add_trace(go.Scatter(
                x=x_hist_dec, y=y_hist_smooth, mode="lines", line=dict(color="#60a5fa", width=2),
                name="Historical (12-mo Avg)", hovertemplate="<b>%{x:.1f}</b><br>Historical: %{y:.1f}" + unit + "<extra></extra>"
            ))
            fig_city.add_trace(go.Scatter(
                x=x_proj, y=y_proj, mode="lines", line=dict(color="#ef4444" if delta_2050 > 0 else "#4ade80", width=3, dash="dash"),
                name="2050 ML Projection", hovertemplate="<b>%{x:.1f}</b><br>Projected: %{y:.1f}" + unit + "<extra></extra>"
            ))
            fig_city.update_layout(
                height=400, title=dict(text=f"Polynomial Forecast to 2050: {city_input}", font=dict(family="Inter", size=14, color="#e2e8f0")),
                xaxis_title="Year", yaxis_title=f"{var_name} ({unit})",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                **clean_layout()
            )

            st.markdown(f"""
            <div style="display:flex; gap:10px; margin-bottom:10px;">
              <div class="card" style="flex:1; border-top:3px solid #60a5fa; padding:1rem;">
                <span style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">Recent Avg</span>
                <div style="font-size:1.5rem; font-weight:700; color:#fff;">{hist_last:.1f}{unit}</div>
              </div>
              <div class="card" style="flex:1; border-top:3px solid {d_color}; padding:1rem;">
                <span style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase;">2050 Projection</span>
                <div style="font-size:1.5rem; font-weight:700; color:{d_color};">{proj_2050:.1f}{unit}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(fig_city, use_container_width=True)

            # ── Rule-based Adaptation Suggestions ────────────────────────────
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            st.markdown("""
            <div style="font-size:0.7rem;color:#4ade80;font-weight:600;letter-spacing:0.1em;
                        text-transform:uppercase;margin-bottom:0.8rem;">
              🌱 What Can Your City Do? — Adaptation Suggestions
            </div>
            <div style="font-size:0.78rem;color:#94a3b8;margin-bottom:0.8rem;">
              Based purely on the trend data above — no API needed.
            </div>
            """, unsafe_allow_html=True)

            suggestions = []

            if sel_var == "t2m":
                warming = delta_2050
                if warming > 3.0:
                    urgency_color = "#ef4444"
                    urgency_label = "🚨 Critical — Action Needed Now"
                    suggestions += [
                        ("🌳", "Urban Forest Corridors",
                         f"At +{warming:.1f}°C, street-level heat becomes dangerous. Plant tree corridors on main roads — "
                         f"tree canopy can reduce surface temperature by 3–8°C locally."),
                        ("🏗️", "Cool Roofs & Pavements Mandate",
                         "Require white or reflective roofing on all new construction. "
                         "Reflective surfaces reduce indoor cooling load by up to 40% and lower neighbourhood air temp."),
                        ("💧", "Emergency Cooling Centres Network",
                         f"With projected {proj_2050:.1f}°C averages, vulnerable populations need guaranteed cool refuges. "
                         "Map and fund at least one cooling centre per km² in dense areas."),
                        ("⚡", "Grid Resilience for Peak Demand",
                         "Extreme heat drives AC load spikes that crash grids. "
                         "Invest in distributed solar + battery storage to prevent blackouts during heatwaves."),
                        ("🌊", "Rainwater Harvesting & Grey Water Reuse",
                         "Higher temperatures increase evaporation and drought risk. "
                         "Mandate rainwater collection in all buildings over 100m²."),
                    ]
                elif warming > 1.5:
                    urgency_color = "#f59e0b"
                    urgency_label = "⚠️ Moderate — Plan and Build Now"
                    suggestions += [
                        ("🌿", "Green Roofs & Vertical Gardens",
                         f"A +{warming:.1f}°C trend is significant. Green roofs insulate buildings, "
                         "reduce stormwater runoff, and cool air by evapotranspiration — typical cooling effect 2–4°C."),
                        ("🚲", "Active Transport Infrastructure",
                         "Reduce car trips to cut urban heat island effect. "
                         "Protected cycle lanes and pedestrian zones lower local emissions and surface heat."),
                        ("🌡️", "Early Warning Heat Alert System",
                         "City-wide SMS/app alerts when heat index crosses thresholds, "
                         "with automatic opening of cooling centres and school schedule adjustments."),
                        ("🏘️", "Neighbourhood Microclimate Audits",
                         "Map heat vulnerability block-by-block. "
                         "Prioritise tree planting and shade structures in high-density, low-canopy areas first."),
                    ]
                else:
                    urgency_color = "#4ade80"
                    urgency_label = "✅ Low — Maintain and Monitor"
                    suggestions += [
                        ("📊", "Continue Long-term Monitoring",
                         f"Projected change of +{warming:.1f}°C is within manageable range. "
                         "Maintain climate monitoring stations and update forecasts every 5 years."),
                        ("🌱", "Preventive Green Infrastructure",
                         "Plant trees now — they take 10–20 years to mature. "
                         "Investing in canopy today means shade is ready when it's needed most."),
                        ("📋", "Climate-Resilient Building Codes",
                         "Update construction standards now to prepare for hotter future summers — "
                         "better insulation, passive cooling design, and orientation guidelines."),
                    ]
            else:
                precip_change = delta_2050
                if precip_change < -5:
                    urgency_color = "#f59e0b"
                    urgency_label = "⚠️ Drying Trend — Water Security Risk"
                    suggestions += [
                        ("💧", "Rainwater Harvesting at Scale",
                         f"Precipitation projected to drop by {abs(precip_change):.1f}mm. "
                         "Mandate rooftop collection across residential and commercial buildings."),
                        ("🌾", "Drought-Resistant Urban Agriculture",
                         "Transition public green spaces to native, drought-tolerant species "
                         "that need 60–80% less water than conventional landscaping."),
                        ("🚿", "Smart Water Metering & Pricing",
                         "Real-time metering + tiered pricing reduces consumption 15–25% "
                         "by making water use visible and expensive above baseline."),
                    ]
                elif precip_change > 5:
                    urgency_color = "#60a5fa"
                    urgency_label = "🌊 Wetting Trend — Flood Risk"
                    suggestions += [
                        ("🏗️", "Permeable Pavement Replacement",
                         f"With +{precip_change:.1f}mm projected increase, impermeable surfaces will cause flooding. "
                         "Replace hard surfaces with permeable alternatives in car parks and low-traffic roads."),
                        ("🌊", "Urban Wetland Restoration",
                         "Restore natural flood plains and wetlands at city edges — "
                         "wetlands absorb 1.5 million litres of water per acre during flood events."),
                        ("🏘️", "Flood Vulnerability Mapping",
                         "Model which neighbourhoods face inundation risk and restrict "
                         "new construction in high-risk zones."),
                    ]
                else:
                    urgency_color = "#4ade80"
                    urgency_label = "✅ Stable Precipitation — Maintain Systems"
                    suggestions += [
                        ("💧", "Maintain Drainage Infrastructure",
                         "Precipitation is relatively stable — keep storm drainage systems "
                         "clear and inspect annually to handle any variability."),
                        ("🌱", "Water-Smart Landscaping",
                         "Use native plant species in public spaces to reduce irrigation demand "
                         "regardless of precipitation trends."),
                    ]

            st.markdown(f"""
            <div style="font-size:0.88rem;color:{urgency_color};font-weight:600;
                        padding:0.6rem 1rem;background:{urgency_color}14;border-radius:8px;
                        border-left:3px solid {urgency_color};margin-bottom:1rem;">
              {urgency_label} &nbsp;·&nbsp; Based on projected change of
              <b>{('+' if delta_2050 >= 0 else '')}{delta_2050:.1f}{unit}</b> by 2050
            </div>
            """, unsafe_allow_html=True)

            for i in range(0, len(suggestions), 2):
                cols = st.columns(2)
                for col, (ico, title, body) in zip(cols, suggestions[i:i+2]):
                    with col:
                        st.markdown(f"""
                        <div style="background:#1a1f2e;border:1px solid rgba(74,222,128,0.15);
                                    border-top:3px solid #4ade80;border-radius:10px;
                                    padding:1rem 1.1rem;margin-bottom:10px;height:100%;">
                          <div style="font-size:1.4rem;margin-bottom:0.4rem">{ico}</div>
                          <div style="font-size:0.85rem;font-weight:700;color:#e2e8f0;
                                      margin-bottom:0.4rem">{title}</div>
                          <div style="font-size:0.78rem;color:#94a3b8;line-height:1.65">{body}</div>
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("""
            <div style="font-size:0.7rem;color:#94a3b8;margin-top:0.5rem;line-height:1.6">
              ℹ️ Suggestions are rule-based and derived from the trend magnitude shown above.
              No external API is used. For city-specific policy detail, consult local climate action plans.
            </div>
            """, unsafe_allow_html=True)