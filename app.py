from flask import Flask, request, render_template, redirect, url_for
import math
import requests
import time

app = Flask(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"

def get_average_speed(lat, lon):
    overpass_url = "http://overpass-api.de/api/interpreter"
    earth_radius = 6371
    zone_radius = 2
    lat_offset = (zone_radius / earth_radius) * (180 / math.pi)
    lon_offset = lat_offset / math.cos(math.radians(lat))
    min_lat, max_lat = lat - lat_offset, lat + lat_offset
    min_lon, max_lon = lon - lon_offset, lon + lon_offset
    
    overpass_query = f"""
    [out:json];
    way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]
    ({min_lat},{min_lon},{max_lat},{max_lon});
    out center;
    """
    
    response = requests.get(overpass_url, params={"data": overpass_query})
    av_speed, av_element = 0, 1
    if response.status_code == 200:
        data = response.json()
        for element in data["elements"]:
            if 'maxspeed' in element.get('tags', {}):
                try:
                    av_speed += int(element['tags']['maxspeed'])
                    av_element += 1
                except ValueError:
                    pass
    return av_speed / av_element if av_element > 1 else 0

def get_building_density(lat, lon):
    lat = float(lat)
    lon = float(lon)
    overpass_url = "http://overpass-api.de/api/interpreter"

    earth_radius = 6371
    zone_radius = 2

    lat_offset = (zone_radius / earth_radius) * (180 / math.pi)
    lon_offset = lat_offset / math.cos(math.radians(lat))
    
    min_lat = lat - lat_offset
    max_lat = lat + lat_offset

    min_lon = lon - lon_offset
    max_lon = lon + lon_offset
    print(f'coords: {lat},{lon}')

    overpass_query = f"""
    [out:json];
    way["building"]({min_lat},{min_lon},{max_lat},{max_lon});
    out count;
    """

    # Send the request
    response = requests.get(overpass_url, params={"data": overpass_query})

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        building_count = data.get("elements", [{}])[0].get("tags", {}).get("total", 0)
        print(f"Number of buildings in the area: {building_count}")

        # Simple density check
        if int(building_count) > 10000:
            print("This is a dense area!")
        else:
            print("This area is not very dense.")
        return int(building_count)
    else:
        print("Error fetching data:", response.status_code)
        return 0


def get_land_type(lat, lon):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    is_in({lat},{lon})->.a;
    area.a["landuse"];
    out tags;
    """
    response = requests.get(overpass_url, params={"data": overpass_query})
    if response.status_code == 200:
        elements = response.json().get("elements", [])
        return elements[0].get("tags", {}).get("landuse", "Unknown") if elements else "Unknown"
    return "Unknown"

def get_mountains_nearby(lat, lon, radius=2):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    node(around:{radius * 1000},{lat},{lon})["natural"="peak"];
    out;
    """
    response = requests.get(overpass_url, params={"data": overpass_query})
    if response.status_code == 200:
        return len(response.json().get("elements", [])) > 0
    return False



def get_elevation(lat,lon):
    lat = float(lat)
    lon = float(lon)
    elevation = 0
    try:
        response = requests.get(f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}")
        if response.status_code == 200:
            elevation = response.json()["results"][0]["elevation"]
            return elevation
        else:
            return elevation
    except:
        return elevation

def calculate_5g_antenna_config(building_density, land_type, mountains, elevation, avg_speed):
    if mountains:
        frequency = "3.5 GHz"
        subcarrier_size = "30 kHz"
        cycle_mode = "Extended"
        output_power = "High"
        radius_km = 1.5
    elif avg_speed > 80:
        frequency = "700 MHz"
        subcarrier_size = "15 kHz"
        cycle_mode = "Extended"
        output_power = "High"
        radius_km = 10
    elif building_density > 500:
        frequency = "26 GHz"
        subcarrier_size = "120 kHz"
        cycle_mode = "Normal"
        output_power = "Medium"
        radius_km = 0.5
    elif building_density > 100:
        frequency = "3.5 GHz"
        subcarrier_size = "30 kHz"
        cycle_mode = "Normal"
        output_power = "Medium"
        radius_km = 2
    else:
        frequency = "700 MHz"
        subcarrier_size = "15 kHz"
        cycle_mode = "Extended"
        output_power = "Low"
        radius_km = 10
    
    return {
        "Frequency": frequency,
        "Subcarrier Size": subcarrier_size,
        "Cyclic Prefix Mode": cycle_mode,
        "Output Power": output_power,
        "Coverage Radius": f"{radius_km} km"
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    lat, lon = request.form['lat'], request.form['lon']
    
    try:
        lat = float(lat)
        lon = float(lon)
    except:
        return redirect(url_for('home'))
    building_density = get_building_density(lat, lon)
    land_type = get_land_type(lat, lon)
    mountains = get_mountains_nearby(lat, lon)
    elevation = get_elevation(lat, lon)
    avg_speed = get_average_speed(float(lat), float(lon))
    antenna_config = calculate_5g_antenna_config(building_density, land_type, mountains, elevation, avg_speed)
     
    return render_template('result.html', lat=lat, lon=lon, 
                           building_density=building_density, land_type=land_type,
                           mountains=mountains, elevation=elevation, avg_speed=int(avg_speed),
                           antenna_config=antenna_config)

if __name__ == '__main__':
    app.run(debug=True, port=8080, host="0.0.0.0")

