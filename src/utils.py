import numpy as np
import requests

try:
    from geopy.geocoders import Nominatim
    GEOPY_OK = True
except ImportError:
    GEOPY_OK = False

def get_city_suggestions(query):
    if not query or len(query) < 2:
        return []
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "featuretype": "city",
            "limit": 5
        }
        resp = requests.get(url, params=params, headers={"User-Agent": "pce_v3_autocomplete"}, timeout=5)
        if resp.ok:
            data = resp.json()
            if not data:
                params.pop("featuretype")
                resp = requests.get(url, params=params, headers={"User-Agent": "pce_v3_autocomplete"}, timeout=5)
                if resp.ok: data = resp.json()
                
            results = []
            for item in data:
                name = item.get("display_name", "")
                addrs = item.get("address", {})
                osm_class = item.get("class", "")
                
                if any(k in addrs for k in ["city", "town", "village", "county", "state"]) or osm_class in ["place", "boundary"]:
                    results.append({
                        "name": name,
                        "lat": float(item["lat"]),
                        "lon": float(item["lon"])
                    })
            return results
    except Exception:
        pass
    return []

def do_geocode(name):
    if not GEOPY_OK:
        return None, None
    try:
        loc = Nominatim(user_agent="pce_v3").geocode(
            name,
            addressdetails=True,
            timeout=5
        )
        if loc and loc.raw:
            osm_type = loc.raw.get("osm_type", "")
            osm_class = loc.raw.get("class", "")
            addrs = loc.raw.get("address", {})
            
            if any(k in addrs for k in ["city", "town", "village", "county", "state"]) or osm_class in ["place", "boundary"]:
                return loc.latitude, loc.longitude
    except Exception:
        pass
    return None, None

def nearest_idx(ds, lat, lon):
    li = int(np.abs(ds.latitude.values - lat).argmin())
    lj = int(np.abs(ds.longitude.values - lon).argmin())
    return li, lj

def to_celsius(da):
    return da - 273.15 if da.attrs.get("units") == "K" else da
