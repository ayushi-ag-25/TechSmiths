# 🌍 PyClimaExplorer

**Turning climate data into stories — for researchers and the curious alike**

Built by **TechSmiths** @ IIT(BHU) Hackathon 2026

---

## 🚀 Quick Start (2 minutes)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API key (for Story Mode AI)
```bash
# Windows
set ANTHROPIC_API_KEY=your_key_here

# Mac/Linux
export ANTHROPIC_API_KEY=your_key_here
```
> Get a free key at https://console.anthropic.com — Story Mode works without it but shows an error.

### 3. Run the app
```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

---

## 🌐 Deploy to Streamlit Cloud (Free, 5 minutes)

1. Push this folder to a **GitHub repository**
2. Go to https://share.streamlit.io
3. Click **New app** → select your repo → set `app.py` as the main file
4. Add `ANTHROPIC_API_KEY` in **Secrets** (Settings → Secrets)
5. Click **Deploy** — you get a live public URL!

---

## 📊 Features

| Mode | What it does |
|------|-------------|
| 🗺️ Normal Mode | Interactive global heatmap + city search + 30-year time series |
| ⚖️ Compare Mode | Side-by-side heatmaps for two years + dual time series |
| 🌐 3D Globe | PyDeck 3D column map — rotate and zoom the planet |
| 📖 Story Mode | Claude AI explains climate events in plain English |

---

## 📁 Data

### Built-in sample
The app ships with a synthetic ERA5-like dataset (1990–2022) so it works out of the box — no download needed.

### Real ERA5 data (recommended for best results)
1. Create a free account at https://cds.climate.copernicus.eu
2. Install the CDS API: `pip install cdsapi`
3. Download temperature data:
```python
import cdsapi
c = cdsapi.Client()
c.retrieve('reanalysis-era5-single-levels', {
    'product_type': 'monthly_averaged_reanalysis',
    'variable': '2m_temperature',
    'year': [str(y) for y in range(1990, 2024)],
    'month': [f'{m:02d}' for m in range(1, 13)],
    'time': '00:00',
    'format': 'netcdf',
}, 'era5_t2m.nc')
```
4. Upload `era5_t2m.nc` via the sidebar file uploader

---

## 🧰 Tech Stack

- **Streamlit** — web framework
- **Xarray** — NetCDF / ERA5 data handling
- **Plotly** — interactive heatmaps and time series
- **PyDeck** — 3D globe visualization
- **geopy** — city name → coordinates
- **Anthropic Claude** — AI climate storytelling

---

## 👩‍💻 Team TechSmiths

Ayushi Agrawal · Reshmi Yadav · Jhalak Mittal · Neha Malhotra

IIT(BHU) Varanasi · March 2026
