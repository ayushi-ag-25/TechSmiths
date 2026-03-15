import numpy as np
import pandas as pd
import plotly.graph_objects as go
from src.config import CLIM_CS
from src.utils import to_celsius

def clean_layout(**extra):
    base = dict(
        plot_bgcolor="#0f1117",
        paper_bgcolor="#0f1117",
        font=dict(family="Inter, sans-serif", color="#e2e8f0", size=12),
        margin=dict(l=8, r=8, t=40, b=8),
        hoverlabel=dict(
            bgcolor="#181c27", bordercolor="rgba(74,222,128,0.4)",
            font=dict(family="Inter, sans-serif", size=11, color="#e2e8f0"),
        ),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                   color="#94a3b8", showline=True, linecolor="rgba(255,255,255,0.08)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                   color="#94a3b8", showline=True, linecolor="rgba(255,255,255,0.08)"),
    )
    base.update(extra)
    return base

def _build_geo_df(dataset, var, time_idx):
    da = dataset[var].isel(time=time_idx)
    unit = "°C"
    if var == "t2m":
        da = to_celsius(da)
    else:
        da = da * 1000
        unit = "mm"
    lats = dataset.latitude.values
    lons = dataset.longitude.values
    vals = da.values
    # Use ALL grid points — no downsampling — to ensure full coverage
    lat_l, lon_l, z_l = [], [], []
    for i in range(len(lats)):
        for j in range(len(lons)):
            v = float(vals[i, j])
            if not np.isnan(v):
                lat_l.append(float(lats[i]))
                lon_l.append(float(lons[j]))
                z_l.append(v)
    return lat_l, lon_l, z_l, unit, lats, lons

def _marker_size_for_grid(lats, center_lat=None):
    """
    Compute a square marker size (in pixels) large enough to tile the
    geo projection without gaps. ERA5 is 2.5-degree grid; at the default
    natural-earth projection rendered at ~700 px wide, 1 degree ≈ 1.94 px.
    We add a small overlap factor (1.25) to eliminate gaps at all zoom levels.
    """
    if len(lats) > 1:
        deg_spacing = abs(float(lats[1]) - float(lats[0]))
    else:
        deg_spacing = 2.5
    # pixels per degree at natural-earth full-globe width ~700px
    px_per_deg = 700.0 / 360.0
    size = deg_spacing * px_per_deg * 1.35   # 1.35 overlap to close gaps
    if center_lat is not None:
        # when zoomed in, markers should be slightly smaller
        size = max(4, size * 0.7)
    return max(4, round(size))

def make_heatmap(dataset, var, time_idx, title="", zmin=None, zmax=None, cs=None, height=460, center_lat=None, center_lon=None, zoom=1):
    if cs is None:
        cs = CLIM_CS
    lat_l, lon_l, z_l, unit, lats, lons = _build_geo_df(dataset, var, time_idx)
    if zmin is None:
        zmin = min(z_l)
    if zmax is None:
        zmax = max(z_l)

    msize = _marker_size_for_grid(lats, center_lat)

    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lat=lat_l,
        lon=lon_l,
        mode="markers",
        marker=dict(
            symbol="square",
            color=z_l,
            colorscale=cs,
            cmin=zmin,
            cmax=zmax,
            size=msize,
            opacity=0.92,
            colorbar=dict(
                title=dict(text=unit, font=dict(family="Inter", size=10, color="#94a3b8")),
                thickness=12,
                len=0.7,
                tickfont=dict(family="Inter", size=10, color="#94a3b8"),
                bgcolor="rgba(15,17,23,0.9)",
                bordercolor="rgba(255,255,255,0.1)",
                x=1.01,
            ),
            line=dict(width=0),
        ),
        hovertemplate=(
            "<b>%{lat:.1f}°, %{lon:.1f}°</b><br>"
            "Value: <b>%{marker.color:.1f} " + unit + "</b>"
            "<extra></extra>"
        ),
    ))
    geo_opts = dict(
        showland=True,    landcolor="rgba(28,37,54,0.95)",
        showocean=True,   oceancolor="rgba(10,15,25,0.97)",
        showlakes=True,   lakecolor="rgba(12,20,35,0.97)",
        showcountries=True, countrycolor="rgba(255,255,255,0.55)", countrywidth=1.2,
        showcoastlines=True, coastlinecolor="rgba(255,255,255,0.70)", coastlinewidth=1.2,
        bgcolor="#0f1117",
        framecolor="rgba(255,255,255,0.08)",
        framewidth=1,
        lonaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", gridwidth=0.4),
        lataxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", gridwidth=0.4),
    )
    if center_lat is not None and center_lon is not None:
        geo_opts["projection"] = dict(type="natural earth", scale=zoom)
        geo_opts["center"] = dict(lat=center_lat, lon=center_lon)
    else:
        geo_opts["projection_type"] = "natural earth"
        geo_opts["lonaxis"]["range"] = [-180, 180]
        geo_opts["lataxis"]["range"] = [-90, 90]

    fig.update_layout(
        geo=geo_opts,
        height=height,
        margin=dict(l=0, r=70, t=44, b=0),
        title=dict(text=title, font=dict(family="Inter", size=12, color="#e2e8f0", weight=600), x=0.01),
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        font=dict(family="Inter", color="#e2e8f0"),
        hoverlabel=dict(bgcolor="#181c27", bordercolor="rgba(74,222,128,0.4)",
                        font=dict(family="Inter", size=11)),
    )
    return fig

def make_timeseries(dataset, var, li, lj, label="", color="#4ade80", fillcolor="rgba(74,222,128,0.06)",
                    show_caption=True):
    da = dataset[var].isel(latitude=li, longitude=lj)
    unit = "°C" if var == "t2m" else "mm"
    var_name = "Temperature" if var == "t2m" else "Precipitation"
    if var == "t2m":
        da = to_celsius(da)
    else:
        da = da * 1000

    times_x = pd.to_datetime(dataset.time.values)
    y_vals   = da.values

    s = pd.Series(y_vals, index=times_x)
    rolling = s.rolling(12, center=True, min_periods=6).mean()

    x_num  = np.arange(len(y_vals), dtype=float)
    coeffs = np.polyfit(x_num[~np.isnan(y_vals)], y_vals[~np.isnan(y_vals)], 1)
    trend_y = np.polyval(coeffs, x_num)
    slope_dec = coeffs[0] * 120
    if abs(slope_dec) < 0.05:
        trend_label = "Trend: Stable"
    elif slope_dec > 0:
        trend_label = f"Trend: ▲ +{slope_dec:.2f} {unit}/decade (Warming)"
    else:
        trend_label = f"Trend: ▼ {slope_dec:.2f} {unit}/decade (Cooling)"

    valid_mask = ~np.isnan(y_vals)
    if valid_mask.sum() > 0:
        max_idx = int(np.nanargmax(y_vals))
        min_idx = int(np.nanargmin(y_vals))
        max_val, min_val = float(y_vals[max_idx]), float(y_vals[min_idx])
        max_time, min_time = times_x[max_idx], times_x[min_idx]
    else:
        max_idx = min_idx = 0
        max_val = min_val = 0.0
        max_time = min_time = times_x[0]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=times_x, y=y_vals,
        mode="lines",
        line=dict(width=1.5, color=color),
        fill="tozeroy",
        fillcolor=fillcolor,
        name=f"Monthly {var_name}",
        hovertemplate=(
            "<b>%{x|%B %Y}</b><br>"
            f"{var_name}: <b>%{{y:.1f}} {unit}</b>"
            "<extra></extra>"
        ),
        opacity=0.7,
    ))

    fig.add_trace(go.Scatter(
        x=times_x, y=rolling.values,
        mode="lines",
        line=dict(width=3, color="#f59e0b", dash="solid"),
        name="12-Month Average",
        hovertemplate=(
            "<b>%{x|%B %Y}</b><br>"
            f"12-Month Avg: <b>%{{y:.1f}} {unit}</b>"
            "<extra></extra>"
        ),
    ))

    fig.add_trace(go.Scatter(
        x=times_x, y=trend_y,
        mode="lines",
        line=dict(width=2, color="#ef4444", dash="dot"),
        name=trend_label,
        hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=[max_time], y=[max_val],
        mode="markers+text",
        marker=dict(symbol="triangle-up", size=12, color="#ef4444",
                    line=dict(color="#fff", width=1)),
        text=[f"Peak: {max_val:.1f}{unit}"],
        textposition="top right",
        textfont=dict(size=10, color="#ef4444"),
        name=f"All-time High",
        hovertemplate=f"<b>Highest recorded</b><br>{max_val:.1f} {unit} · %{{x|%b %Y}}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=[min_time], y=[min_val],
        mode="markers+text",
        marker=dict(symbol="triangle-down", size=12, color="#60a5fa",
                    line=dict(color="#fff", width=1)),
        text=[f"Low: {min_val:.1f}{unit}"],
        textposition="bottom right",
        textfont=dict(size=10, color="#60a5fa"),
        name=f"All-time Low",
        hovertemplate=f"<b>Lowest recorded</b><br>{min_val:.1f} {unit} · %{{x|%b %Y}}<extra></extra>",
    ))

    title_text = (
        f"📈 Monthly {var_name} Over Time"
        + (f" — {label}" if label else "")
    )

    fig.update_layout(
        height=360,
        xaxis_title="Year",
        yaxis_title=f"{var_name} ({unit})",
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.01,
            xanchor="left", x=0,
            font=dict(family="Inter", size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        **clean_layout(
            title=dict(
                text=title_text,
                font=dict(size=13, color="#e2e8f0", weight=600),
                x=0.0,
            ),
            xaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                color="#94a3b8", showline=True, linecolor="rgba(255,255,255,0.08)",
                tickformat="%Y",
                dtick="M24",
            ),
            yaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                color="#94a3b8", showline=True, linecolor="rgba(255,255,255,0.08)",
                zeroline=True, zerolinecolor="rgba(255,255,255,0.12)", zerolinewidth=1,
            ),
        ),
    )
    return fig
