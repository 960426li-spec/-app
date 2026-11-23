import math
import requests
from flask import Flask, render_template, request

app = Flask(__name__, template_folder="../templates")

# 請將信箱改成可聯絡的信箱。Nominatim 要求使用可識別的 User-Agent。
HEADERS = {
    "User-Agent": "NearbyFoodFlaskApp/1.0 (contact: your-email@example.com)"
}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

CATEGORY_NAMES = {
    "restaurant": "餐廳",
    "cafe": "咖啡廳",
    "fast_food": "速食店",
    "food_court": "美食街",
}
ALLOWED_CATEGORIES = {"all", "restaurant", "cafe", "fast_food"}
ALLOWED_RADII = {300, 500, 1000}


def render_page(**kwargs):
    """統一提供模板預設值，避免不同路由漏傳參數。"""
    defaults = {
        "restaurants": None,
        "error": None,
        "location": "",
        "radius": 500,
        "category": "all",
        "searched": False,
    }
    defaults.update(kwargs)
    return render_template("index.html", **defaults)


def haversine_m(lat1, lon1, lat2, lon2):
    """計算兩個經緯度座標間的直線距離（公尺）。"""
    earth_radius = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return earth_radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geocode_location(location):
    params = {"q": location, "format": "jsonv2", "limit": 1}
    response = requests.get(
        NOMINATIM_URL, params=params, headers=HEADERS, timeout=10
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def find_nearby_food(lat, lon, radius, category):
    amenities = (
        list(CATEGORY_NAMES)
        if category == "all"
        else [category]
    )

    selectors = []
    for amenity in amenities:
        selectors.append(
            f'node["amenity"="{amenity}"](around:{radius},{lat},{lon});'
        )
        selectors.append(
            f'way["amenity"="{amenity}"](around:{radius},{lat},{lon});'
        )

    query = (
        "[out:json][timeout:10];\n("
        + "\n".join(selectors)
        + "\n);\nout center tags;"
    )

    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()

    results = []
    seen = set()

    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        amenity = tags.get("amenity")
        if amenity not in CATEGORY_NAMES:
            continue

        if "lat" in element and "lon" in element:
            shop_lat = float(element["lat"])
            shop_lon = float(element["lon"])
        elif element.get("center"):
            shop_lat = float(element["center"]["lat"])
            shop_lon = float(element["center"]["lon"])
        else:
            continue

        distance = haversine_m(lat, lon, shop_lat, shop_lon)
        if distance > radius:
            continue

        osm_type = element.get("type", "object")
        osm_id = element.get("id")
        unique_key = (osm_type, osm_id)
        if unique_key in seen:
            continue
        seen.add(unique_key)

        street = tags.get("addr:street", "")
        house_number = tags.get("addr:housenumber", "")
        address = " ".join(part for part in (street, house_number) if part)
        if not address:
            address = "尚未提供地址"

        results.append({
            "name": tags.get("name") or "未命名店家",
            "category": CATEGORY_NAMES[amenity],
            "cuisine": tags.get("cuisine") or "未標示",
            "opening_hours": tags.get("opening_hours") or "尚未確認",
            "address": address,
            "distance": round(distance),
            "google_maps_url": (
                "https://www.google.com/maps/dir/?api=1"
                f"&destination={shop_lat},{shop_lon}"
            ),
            "osm_url": (
                "https://www.openstreetmap.org/"
                f"?mlat={shop_lat}&mlon={shop_lon}"
                f"#map=18/{shop_lat}/{shop_lon}"
            ),
        })

    results.sort(key=lambda item: item["distance"])
    return results[:30]


@app.get("/")
def index():
    return render_page()


@app.get("/search")
def search():
    location = request.args.get("location", "").strip()
    lat_text = request.args.get("lat", "").strip()
    lon_text = request.args.get("lon", "").strip()

    try:
        radius = int(request.args.get("radius", "500"))
    except (TypeError, ValueError):
        radius = 500
    if radius not in ALLOWED_RADII:
        radius = 500

    category = request.args.get("category", "all")
    if category not in ALLOWED_CATEGORIES:
        category = "all"

    error = None
    restaurants = None

    if bool(lat_text) != bool(lon_text):
        error = "定位資料不完整，請重新使用目前位置，或直接輸入地點。"
    elif not location and not (lat_text and lon_text):
        error = "請輸入地點，或使用「目前位置」進行搜尋。"
    else:
        try:
            if lat_text and lon_text:
                lat, lon = float(lat_text), float(lon_text)
                if (
                    not math.isfinite(lat)
                    or not math.isfinite(lon)
                    or not -90 <= lat <= 90
                    or not -180 <= lon <= 180
                ):
                    raise ValueError("座標超出有效範圍")
                if not location:
                    location = "目前所在位置"
            else:
                coordinates = geocode_location(location)
                if coordinates is None:
                    error = "找不到這個地點，請確認名稱或地址後再試一次。"
                else:
                    lat, lon = coordinates

            if error is None:
                restaurants = find_nearby_food(lat, lon, radius, category)
                if not restaurants:
                    error = (
                        "這個搜尋範圍內沒有找到符合條件的店家。"
                        "可以改用較大的搜尋範圍，或切換美食類型。"
                    )

        except requests.exceptions.Timeout:
            error = "地圖服務連線逾時，請稍後再試。"
        except requests.exceptions.RequestException:
            error = "目前無法連接地圖服務，請稍後再試。"
        except (ValueError, TypeError, KeyError):
            error = "輸入資料格式不正確，請重新確認地點或定位資訊。"
        except Exception:
            app.logger.exception("Unexpected search error")
            error = "搜尋時發生非預期問題，請稍後再試。"

    return render_page(
        restaurants=restaurants,
        error=error,
        location=location,
        radius=radius,
        category=category,
        searched=True,
    )
