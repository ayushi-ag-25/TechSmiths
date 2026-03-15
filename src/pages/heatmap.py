import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.utils import get_city_suggestions, do_geocode, nearest_idx, to_celsius
from src.plotting import make_heatmap, make_timeseries

def render_heatmap(ds, times, sel_var, VAR_LABELS):
    st.markdown('<div class="sec-header">🗺️ Global Heatmap + Click-to-TimeSeries</div>', unsafe_allow_html=True)

    map_col, ctrl_col = st.columns([3, 1])

    with ctrl_col:
        st.markdown("**Controls**")
        time_idx = st.slider(
            "Time slice",
            0, len(times) - 1, 0,
            help="Move this slider to change which month/year is shown on the map",
        )
        st.caption(f"📅 Selected: **{str(times[time_idx])[:7]}**")

        st.markdown("---")
        st.markdown("**Global Stats** · " + str(times[time_idx])[:7])
        da_slice = ds[sel_var].isel(time=time_idx)
        if sel_var == "t2m":
            da_slice = to_celsius(da_slice)
        else:
            da_slice = da_slice * 1000
        unit_label = "°C" if sel_var == "t2m" else "mm"

        gmax  = float(da_slice.max())
        gmean = float(da_slice.mean())
        gmin  = float(da_slice.min())

        st.markdown(f"""
        <div class="card card-max"><span class="card-val">{gmax:.1f}{unit_label}</span><span class="card-label">🔴 Hottest spot</span></div>
        <div class="card card-mean"><span class="card-val">{gmean:.1f}{unit_label}</span><span class="card-label">🟡 Global average</span></div>
        <div class="card card-min"><span class="card-val">{gmin:.1f}{unit_label}</span><span class="card-label">🔵 Coldest spot</span></div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Search & Zoom to City**")
        
        if "search_key_suffix" not in st.session_state:
            st.session_state.search_key_suffix = 0
            
        search_widget_key = f"city_search_{st.session_state.search_key_suffix}"
        search_q = st.text_input("City name", placeholder="Type to search (e.g. Delhi)...", key=search_widget_key)
        
        city_lat = city_lon = None
        selected_city_name = None
        
        if search_q:
            suggestions = get_city_suggestions(search_q)
            if suggestions:
                options = {s["name"]: s for s in suggestions}
                selected_name = st.selectbox(
                    "Select match:", 
                    options=list(options.keys()),
                    help="Pick the exact city from the suggestions."
                )
                
                if selected_name:
                    selected_city_name = selected_name.split(",")[0]
                    city_lat = options[selected_name]["lat"]
                    city_lon = options[selected_name]["lon"]
            else:
                st.error("⚠️ City not found or invalid. Please try a different spelling.")
                
        if city_lat is not None or st.session_state.clicked_lat is not None:
             if st.button("🌍 Reset to Global View", use_container_width=True):
                 st.session_state.clicked_lat = None
                 st.session_state.clicked_lon = None
                 st.session_state.search_key_suffix += 1
                 st.rerun()

    with map_col:
        time_label = str(times[time_idx])[:7]
        st.markdown(
            '<div class="click-hint">👆 <b>Click any coloured dot</b> on the map below to see a 30-year time series for that location</div>',
            unsafe_allow_html=True,
        )
        fig_map = make_heatmap(
            ds, sel_var, time_idx,
            title=f"{VAR_LABELS.get(sel_var,sel_var)} · {time_label}",
            center_lat=city_lat, center_lon=city_lon, zoom=4 if city_lat is not None else 1
        )

        if city_lat is not None and selected_city_name is not None:
            li_c, lj_c = nearest_idx(ds, city_lat, city_lon)
            city_da = ds[sel_var].isel(time=time_idx, latitude=li_c, longitude=lj_c)
            city_val = float(to_celsius(city_da)) if sel_var == "t2m" else float(city_da) * 1000
            fig_map.add_trace(go.Scattergeo(
                lat=[city_lat], lon=[city_lon],
                mode="markers+text",
                marker=dict(size=14, color="#4ade80", symbol="star",
                            line=dict(color="#0f1117", width=1.5)),
                text=[selected_city_name],
                textposition="top right",
                textfont=dict(color="#4ade80", size=11, family="Inter"),
                showlegend=False,
                hovertemplate=f"<b>{selected_city_name}</b><br>Value: {city_val:.1f} {unit_label}<extra></extra>",
            ))
            with ctrl_col:
                st.markdown(f"""
                <div class="card card-city">
                  <span class="card-val">{city_val:.1f}{unit_label}</span>
                  <span class="card-label">📍 {selected_city_name}</span>
                </div>
                """, unsafe_allow_html=True)

        selection = st.plotly_chart(
            fig_map,
            use_container_width=True,
            key="heatmap_main",
            on_select="rerun",
            selection_mode="points",
        )

        clicked_lat = clicked_lon = None
        if selection and selection.get("selection") and selection["selection"].get("points"):
            pt = selection["selection"]["points"][0]
            clicked_lat = pt.get("lat")
            clicked_lon = pt.get("lon")
            st.session_state.clicked_lat = clicked_lat
            st.session_state.clicked_lon = clicked_lon
        elif st.session_state.clicked_lat is not None:
            clicked_lat = st.session_state.clicked_lat
            clicked_lon = st.session_state.clicked_lon

        if clicked_lat is not None and clicked_lon is not None:
            li, lj = nearest_idx(ds, clicked_lat, clicked_lon)
            actual_lat = float(ds.latitude.values[li])
            actual_lon = float(ds.longitude.values[lj])
            st.markdown(f"### 📈 30-Year Trend at ({actual_lat:.1f}°, {actual_lon:.1f}°)")
            fig_ts = make_timeseries(ds, sel_var, li, lj,
                                     label=f"{actual_lat:.1f}°N, {actual_lon:.1f}°E")
            st.plotly_chart(fig_ts, use_container_width=True)
            st.caption(
                "📌 **How to read this chart:** Each spike = one month's reading. "
                "🟡 Gold line = 12-month rolling average (smoothed trend). "
                "🔴 Dotted red = long-term direction (warming/cooling). "
                "▲ Red triangle = all-time highest · ▼ Blue triangle = all-time lowest. "
                "Hover any point for exact value & month."
            )

            dl_da = ds[sel_var].isel(latitude=li, longitude=lj)
            if sel_var == "t2m":
                dl_da = to_celsius(dl_da)
            else:
                dl_da = dl_da * 1000
            df_exp = pd.DataFrame({"time": ds.time.values, sel_var: dl_da.values})
            st.download_button(
                "⬇ Export CSV for this location",
                df_exp.to_csv(index=False).encode(),
                file_name=f"climate_{actual_lat:.1f}_{actual_lon:.1f}.csv",
                mime="text/csv",
            )
        elif city_lat is not None and selected_city_name is not None:
            li, lj = nearest_idx(ds, city_lat, city_lon)
            st.markdown(f"### 📈 30-Year Trend — {selected_city_name}")
            fig_ts = make_timeseries(ds, sel_var, li, lj, label=selected_city_name)
            st.plotly_chart(fig_ts, use_container_width=True)
            st.caption(
                "📌 **How to read this chart:** Each spike = one month's reading. "
                "🟡 Gold line = 12-month rolling average (smoothed trend). "
                "🔴 Dotted red = long-term direction. "
                "▲ peak and ▼ lowest values are marked. Hover for details."
            )
            dl_da = ds[sel_var].isel(latitude=li, longitude=lj)
            if sel_var == "t2m":
                dl_da = to_celsius(dl_da)
            else:
                dl_da = dl_da * 1000
            df_exp = pd.DataFrame({"time": ds.time.values, sel_var: dl_da.values})
            st.download_button("⬇ Export CSV", df_exp.to_csv(index=False).encode(),
                               file_name=f"{selected_city_name}_{sel_var}.csv", mime="text/csv")
