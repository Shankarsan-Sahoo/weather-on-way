import requests
import polyline
from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt
from functools import lru_cache
import os
import time
from requests.exceptions import Timeout, ConnectionError

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENWEATHER_KEY = os.getenv("OWM_API_KEY")


# -------------------------------
# 1. Haversine distance
# -------------------------------
def haversine(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371.0  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    x = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(x))


# -------------------------------
# 2. Get route from Google
# -------------------------------
def get_route(origin, destination, mode="driving", max_retries=3):
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {"origin": origin, "destination": destination, "mode": mode, "key": GOOGLE_API_KEY}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            res = response.json()
            
            if res["status"] != "OK":
                raise Exception(res.get("error_message", res))
                
            route = res["routes"][0]["legs"][0]
            poly = res["routes"][0]["overview_polyline"]["points"]
            distance = route["distance"]["value"] / 1000  # km
            duration = route["duration"]["value"] / 60    # mins
            coords = polyline.decode(poly)
            return distance, duration, coords
            
        except (Timeout, ConnectionError) as e:
            if attempt < max_retries - 1:
                # Wait before retrying (exponential backoff)
                time.sleep(1 * (2 ** attempt))
                continue
            else:
                raise Exception(f"Connection error after {max_retries} attempts: {str(e)}")
        except Exception as e:
            raise Exception(f"Error getting route: {str(e)}")


# -------------------------------
# 3. Sample points along polyline
# -------------------------------
def sample_points(coords, step_km=10):
    sampled = [coords[0]]
    cum_dist = 0.0
    last_pt = coords[0]
    for pt in coords[1:]:
        d = haversine(last_pt, pt)
        cum_dist += d
        if cum_dist >= step_km:
            sampled.append(pt)
            cum_dist = 0.0
            last_pt = pt
    if sampled[-1] != coords[-1]:
        sampled.append(coords[-1])
    return sampled


# -------------------------------
# 4. Reverse geocode (cached)
# -------------------------------
@lru_cache(maxsize=None)
def get_place(lat, lon, max_retries=3):
    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {"latlng": f"{lat},{lon}", "key": GOOGLE_API_KEY, "language": "en"}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            res = response.json()
            
            if "results" in res and res["results"]:
                for comp in res["results"][0]["address_components"]:
                    if "locality" in comp["types"] or "sublocality_level_1" in comp["types"]:
                        return comp["long_name"]
                return res["results"][0]["formatted_address"].split(",")[0]
            return f"{lat:.2f},{lon:.2f}"
            
        except (Timeout, ConnectionError) as e:
            if attempt < max_retries - 1:
                # Wait before retrying (exponential backoff)
                time.sleep(1 * (2 ** attempt))
                continue
            else:
                # Return coordinates if we can't get the place name
                return f"{lat:.2f},{lon:.2f}"
        except Exception as e:
            # Return coordinates if there's any other error
            return f"{lat:.2f},{lon:.2f}"


# -------------------------------
# 5. Weather forecast (cached)
# -------------------------------
@lru_cache(maxsize=None)
def get_weather(lat, lon, max_retries=3):
    url = f"https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY, "units": "metric"}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            res = response.json()
            
            if "list" not in res:
                return {"description": "No Forecast", "temp": "N/A"}
            
            fc = res["list"][0]  # nearest forecast
            rain_prob = fc.get("pop", 0) * 100
            temp = fc["main"]["temp"]
            
            if rain_prob > 70:
                description = f"Heavy Rain 🌧️ ({rain_prob:.0f}%)"
            elif rain_prob > 40:
                description = f"Moderate Rain 🌦️ ({rain_prob:.0f}%)"
            elif rain_prob > 10:
                description = f"Light Rain 🌤️ ({rain_prob:.0f}%)"
            else:
                description = f"Clear ☀️ ({rain_prob:.0f}%)"
                
            return {
                "description": description,
                "temp": round(temp, 1)
            }
            
        except (Timeout, ConnectionError) as e:
            if attempt < max_retries - 1:
                # Wait before retrying (exponential backoff)
                time.sleep(1 * (2 ** attempt))
                continue
            else:
                # Return a default forecast if we can't get the weather
                return {"description": "Forecast Unavailable", "temp": "N/A"}
        except Exception as e:
            # Return a default forecast if there's any other error
            return {"description": "Forecast Error", "temp": "N/A"}


# -------------------------------
# 6. Main route forecast (returns list)
# -------------------------------
def route_forecast(origin, destination, step_km=10, start_time="08:00"):
    distance, duration, coords = get_route(origin, destination)
    points = sample_points(coords, step_km)

    cum_dist = [0.0]
    for i in range(1, len(points)):
        cum_dist.append(cum_dist[-1] + haversine(points[i-1], points[i]))

    avg_speed = 40.0  # km/h
    start_dt = datetime.strptime(start_time, "%H:%M")

    route_data = []
    for i, (lat, lon) in enumerate(points):
        km = cum_dist[i]
        eta = (start_dt + timedelta(hours=km/avg_speed)).strftime("%I:%M %p")
        place = get_place(lat, lon)
        forecast = get_weather(lat, lon)
        route_data.append({
            "distance": round(km, 1),
            "place": place,
            "eta": eta,
            "forecast": forecast
        })
    return route_data
