from flask import Flask, render_template, request
import requests
from requests.exceptions import RequestException

app = Flask(__name__)

# IMPORTANT: Put your email (required by Nominatim / MET Norway)
USER_AGENT = "simple-weather-app/1.0 (your-email@example.com)"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MET_NO_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"


def geocode_city(city_name):
    """Return (lat, lon, error_msg)."""
    params = {"q": city_name, "format": "json", "limit": 1}
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=8)
    except RequestException as e:
        return None, None, f"Network error contacting geocode service: {e}"

    if resp.status_code != 200:
        return None, None, f"Geocode request failed: HTTP {resp.status_code}"

    try:
        data = resp.json()
    except ValueError:
        return None, None, "Invalid response (non-JSON) received from geocoding service."

    if not data:
        return None, None, "No location found for that city."

    lat = data[0].get("lat")
    lon = data[0].get("lon")

    if not lat or not lon:
        return None, None, "Geocoding returned incomplete coordinates."

    return float(lat), float(lon), None


def get_weather(lat, lon):
    """Return (weather_dict, error_msg)."""
    params = {"lat": lat, "lon": lon}
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(MET_NO_URL, params=params, headers=headers, timeout=10)
    except RequestException as e:
        return None, f"Weather API request failed: {e}"

    if resp.status_code != 200:
        return None, f"Weather API returned HTTP {resp.status_code}"

    try:
        data = resp.json()
    except ValueError:
        return None, "Invalid response (non-JSON) received from weather API."

    timeseries = data.get("properties", {}).get("timeseries")
    if not timeseries:
        return None, "Weather information not available."

    ts = timeseries[0]
    details = ts.get("data", {}).get("instant", {}).get("details", {})
    temperature = details.get("air_temperature")

    summary = None
    for key in ("next_1_hours", "next_6_hours", "next_12_hours"):
        if ts.get("data", {}).get(key, {}).get("summary", {}).get("symbol_code"):
            summary = ts["data"][key]["summary"]["symbol_code"]
            break

    return {
        "temperature": temperature,
        "summary": summary,
        "time": ts.get("time"),
        "lat": lat,
        "lon": lon,
    }, None


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    error = None

    if request.method == "POST":
        city = request.form.get("city")

        lat, lon, err = geocode_city(city)
        if err:
            error = err
        else:
            weather, err = get_weather(lat, lon)
            if err:
                error = err

    return render_template("index.html", weather=weather, error=error)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)