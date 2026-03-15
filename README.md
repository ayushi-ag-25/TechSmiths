# PyClimaExplorer

> **Turn 30+ years of raw climate data into interactive stories, forecasts, and AI-powered insights — in your browser.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![ERA5](https://img.shields.io/badge/Data-ERA5%20%2F%20NetCDF-2ea44f?style=flat-square&logo=databricks&logoColor=white)](https://cds.climate.copernicus.eu)
[![Gemini](https://img.shields.io/badge/AI-Gemini%201.5%20Flash-8E75B2?style=flat-square&logo=googlegemini&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](LICENSE)
[![IIT BHU](https://img.shields.io/badge/Built%20at-IIT(BHU)%20Hackathon%202026-orange?style=flat-square&logo=academia&logoColor=white)](https://iitbhu.ac.in)

[![Live Demo](https://img.shields.io/badge/Live%20Demo-techsmiths.streamlit.app-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://techsmiths-wicbce7pf2zf55npevebdc.streamlit.app/)

Built by **Team TechSmiths** at IIT(BHU) Varanasi — March 2026

---

## Demo

![App Homepage](assets/homepage.jpeg)

---

## What It Does

PyClimaExplorer is a full-stack climate data dashboard that lets researchers, students, and curious users explore Earth's temperature and precipitation records without writing a single line of code.

### Heatmap

Interactive global choropleth + city search + 30-year time series. Click any point on the map to pull up its full climate history.

![Heatmap Global](assets/heatmap_global.jpeg)
![Heatmap City Trend](assets/heatmap_city.jpeg)

### Compare

Side-by-side heatmaps for any two years with dual time series — directly compare climate conditions across decades.

![Compare Mode](assets/compare.jpeg)

### 3D Globe

PyDeck 3D orthographic globe — rotate, zoom, change colour scale and time step interactively.

![Globe Mode](assets/globe.jpeg)

### Story

Gemini AI narrates real climate events (2003 European Heatwave, 2010 Pakistan Floods, 2022 India Heatwave) with what happened, why, and human impact. Includes a voice narrator and city explore tool.

![Story Overview](assets/story_overview.jpeg)
![Story AI Analysis](assets/story_ai.jpeg)
![Story City Explore](assets/story_city.jpeg)

### Forecast

Pixel-wise ML regression projects temperature/precipitation to any year up to 2100. City-level forecasts include 95% confidence intervals and Gemini-powered risk summaries.

![Forecast Global](assets/forecast_global.jpeg)
![Forecast City](assets/forecast_city.jpeg)

---

## Quick Start

**Prerequisites:** Python 3.9+

### 1. Clone & install

```bash
git clone https://github.com/<your-username>/pyclimaexplorer.git
cd pyclimaexplorer
pip install -r requirements.txt
```

### 2. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) — the app loads with a built-in ERA5 sample dataset immediately. No sidebar, no setup required.

---

## Project Structure

```
pyclimaexplorer/
├── app.py                    # Main Streamlit entry point
├── requirements.txt
├── .streamlit/
│   └── config.toml           # Theme configuration
└── src/
    ├── config.py             # CSS, session state, API keys
    ├── data.py               # ERA5 loading & synthetic sample generation
    ├── utils.py              # Geocoding, nearest-index lookup, unit helpers
    ├── plotting.py           # Shared Plotly layout helpers & colorscale
    └── pages/
        ├── heatmap.py        # Normal mode
        ├── compare.py        # Compare mode
        ├── globe.py          # 3D Globe mode
        ├── story.py          # Story / AI mode
        └── future_scope.py   # Forecast mode (ML + Gemini)
```

---

## Data Sources

### Built-in sample (zero setup)
The app ships with a synthetic ERA5-like dataset spanning **1990–2022** covering both `t2m` (2-metre temperature) and `tp` (total precipitation). It works out of the box — no download, no account.

### Real ERA5 data (recommended for research)

1. Create a free account at [https://cds.climate.copernicus.eu](https://cds.climate.copernicus.eu)
2. Install the CDS API: `pip install cdsapi`
3. Run this download script:

```python
import cdsapi

c = cdsapi.Client()
c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'monthly_averaged_reanalysis',
        'variable': '2m_temperature',
        'year': [str(y) for y in range(1990, 2024)],
        'month': [f'{m:02d}' for m in range(1, 13)],
        'time': '00:00',
        'format': 'netcdf',
    },
    'era5_t2m.nc'
)
```

4. In the app, toggle **off** the sample data switch and upload your `era5_t2m.nc` file.

---

## How the ML Forecast Works

The **Forecast Mode** runs a **pixel-wise regression** across every spatial grid point:

```
For each (lat, lon) pixel:
  1. Extract the full monthly time series (1990–2022)
  2. Fit a Polynomial (degree 2) regression on decimal year
  3. Project forward to the target year (2030–2100)
  4. Compute decadal rate-of-change for risk ranking
```

This means the app trains **~10,000+ independent models** simultaneously (one per grid cell) using `numpy.linalg.lstsq` — fast enough to run in a browser thanks to `@st.cache_data`.

City-level forecasts extend to 2050 and include **95% confidence intervals** that widen with projection distance, giving an honest uncertainty representation.

> **Limitations:** This is a trend extrapolation, not a climate simulation. Results should be interpreted as illustrative projections, not scientific predictions. For research use, see CMIP6 models.

---

## Tech Stack

| Library | Purpose |
|---------|---------|
| [![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io) | Web framework & reactive UI |
| [![Xarray](https://img.shields.io/badge/Xarray-2ea44f?style=flat-square&logo=python&logoColor=white)](https://xarray.pydata.org) | NetCDF / ERA5 data handling |
| [![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)](https://plotly.com/python/) | Interactive heatmaps, time series, globe |
| [![PyDeck](https://img.shields.io/badge/PyDeck-blue?style=flat-square&logo=mapbox&logoColor=white)](https://deckgl.readthedocs.io) | 3D column map visualization |
| [![geopy](https://img.shields.io/badge/geopy-gray?style=flat-square&logo=openstreetmap&logoColor=white)](https://geopy.readthedocs.io) | City name to lat/lon geocoding |
| [![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org) | Pixel-wise regression, statistics |
| [![Gemini](https://img.shields.io/badge/Gemini%201.5%20Flash-8E75B2?style=flat-square&logo=googlegemini&logoColor=white)](https://aistudio.google.com) | Climate storytelling & risk summaries |

---

## Deploy to Streamlit Cloud

1. Push this folder to a **public GitHub repository**
2. Go to [https://share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set `app.py` as the main file
4. Click **Deploy** — you get a live public URL with HTTPS

> The app uses `@st.cache_data` throughout so Streamlit Cloud's resource limits are respected. Cold start is ~15 seconds on the free tier.

---

## Configuration

`.streamlit/config.toml` controls the app theme. To switch to light mode:

```toml
[theme]
base = "light"
primaryColor = "#ef4444"
```

---

## Roadmap

- [ ] Add CMIP6 model comparison alongside the regression forecast
- [ ] Support precipitation anomaly maps (not just absolute values)
- [ ] Add city-to-city climate comparison
- [ ] Export charts as PNG / CSV
- [ ] Multi-language support (Hindi, Spanish, French)

---

## Team TechSmiths

| Member | Role |
|--------|------|
| **Ayushi Agrawal** | Full-stack development · ML forecast module · Feature architecture |
| **Jhalak Mittal** | Feature development · Data pipeline · ERA5 integration · Bug fixes & integration support |
| **Neha Malhotra** | Ideation & product design · Story mode · Gemini AI integration · Feature development |
| **Reshmi Yadav** | UI/UX & frontend development · Plotly visualizations · Technical documentation |

IIT(BHU) Varanasi · Hackathon 2026

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- ERA5 data provided by the [Copernicus Climate Change Service (C3S)](https://cds.climate.copernicus.eu)
- Geocoding powered by [Nominatim / OpenStreetMap](https://nominatim.openstreetmap.org)
- AI features powered by [Google Gemini](https://aistudio.google.com)