import numpy as np
import pandas as pd
import xarray as xr
import streamlit as st

@st.cache_data(show_spinner=False)
def load_sample():
    np.random.seed(42)
    lats  = np.linspace(-90, 90, 73)
    lons  = np.linspace(-180, 180, 144)
    times = pd.date_range("1990-01-01", periods=396, freq="MS")  # Note: in Python 3.12+ freq="ME" may be needed, but MS works well here
    lat_g, _ = np.meshgrid(lats, lons, indexing="ij")
    base = 288 - 0.7 * np.abs(lat_g)
    sea  = 10 * np.sin(np.pi * lat_g / 180)
    t2m_stack, tp_stack = [], []
    for i, t in enumerate(times):
        trend = 0.002 * i
        noise = np.random.normal(0, 2, (73, 144))
        mo    = 5 * np.sin(2 * np.pi * t.month / 12 + lat_g * np.pi / 180)
        t2m_stack.append(base + sea + trend + noise + mo)
        tp_stack.append(np.abs(np.random.normal(3e-5 * np.exp(-0.02 * lat_g**2), 1e-5)))
    return xr.Dataset(
        {
            "t2m": (["time","latitude","longitude"], np.stack(t2m_stack),
                    {"units":"K","long_name":"2m Temperature"}),
            "tp":  (["time","latitude","longitude"], np.stack(tp_stack),
                    {"units":"m","long_name":"Total Precipitation"}),
        },
        coords={"time": times, "latitude": lats, "longitude": lons},
    )
