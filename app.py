from flask import Flask, request, render_template
import math
import requests

app = Flask(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"

def get_average_speed(lat, lon):
    lat = float(lat)
    lon = float(lon)
    overpass_url = "http://overpass-api.de/api/interpreter"

    earth_radius = 6371
    zone_radius = 5

    lat_offset = (zone_radius / earth_radius) * (180 / math.pi)
    lon_offset = lat_offset / math.cos(math.radians(lat))
    
    min_lat = lat - lat_offset
    max_lat = lat + lat_offset

    min_lon = lon - lon_offset
    max_lon = lon + lon_offset
    print(f'coords: {lat},{lon}')

    #overpass_query = f"""
    #[out:json];
    #node["amenity"="restaurant"]({min_lat},{min_lon},{max_lat},{max_lon});
    #out;
    #"""

    #overpass_query = f"""
    #[out:json];
    #node["amenity"="restaurant"]({min_lat},{min_lon},{max_lat},{max_lon});
    #out;
    #"""

    overpass_query = f"""
    [out:json];
    way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]
    ({min_lat},{min_lon},{max_lat},{max_lon});
    out center;
    """

    # Send the request
    response = requests.get(overpass_url, params={"data": overpass_query})

    # Check for success
    print(response.status_code)
    av_speed = 0
    av_element = 1
    if response.status_code == 200:
        data = response.json()
        print(data)
        for element in data["elements"]:
            try:
                if 'maxspeed' in element['tags'].keys():
                    print(f"- element: {element['tags']['maxspeed']}") 
                    av_speed += int(element['tags']['maxspeed']) 
                    av_element += 1 
            except:
                print(element['tags']['maxspeed']+" is not a INT")
        print(f'Average speed is: {av_speed/av_element}')   
        return av_speed / av_element
    else:
        print("Error fetching data:", response.status_code)
        return av_speed

def get_building_density(lat, lon):
    lat = float(lat)
    lon = float(lon)
    overpass_url = "http://overpass-api.de/api/interpreter"

    earth_radius = 6371
    zone_radius = 5

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
        if int(building_count) > 500:
            print("This is a dense area!")
        else:
            print("This area is not very dense.")
        return building_count
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
        if elements:
            landuse = elements[0].get("tags", {}).get("landuse", "Unknown")
            print(f"Land type: {landuse}")
            return landuse
    else:
        print("Error fetching land type data:", response.status_code)

    return "Unknown"

def get_mountains_nearby(lat, lon, radius=5):
    overpass_url = "http://overpass-api.de/api/interpreter"

    overpass_query = f"""
    [out:json];
    node(around:{radius * 1000},{lat},{lon})["natural"="peak"];
    out;
    """

    response = requests.get(overpass_url, params={"data": overpass_query})

    if response.status_code == 200:
        peaks = response.json().get("elements", [])
        if peaks:
            print(f"Mountain(s) detected nearby! {len(peaks)} peaks found.")
            return True
        else:
            print("No mountains nearby.")
            return False
    else:
        print("Error fetching mountain data:", response.status_code)
        return False



def get_elevation(lat,lon):
    lat = float(lat)
    lon = float(lon)

    response = requests.get(f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}")
    if response.status_code == 200:
        elevation = response.json()["results"][0]["elevation"]
        print(f"Elevation: {elevation} meters")
    else:
        print("Error getting elevation data")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    
    lat = request.form['lat']
    lon = request.form['lon']
    print(get_building_density(lat,lon))
    print(get_land_type(lat,lon))
    print(get_mountains_nearby(lat,lon))
    # Call API (Example: Open-Meteo for weather data)
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true"
    }
    response = requests.get(API_URL, params=params)
    data = response.json()

    print(get_elevation(lat,lon))
    print(get_average_speed(lat,lon))
    if "current_weather" in data:
        weather = data["current_weather"]
        return render_template('result.html', lat=lat, lon=lon, weather=weather)
    else:
        return "Error retrieving data"

if __name__ == '__main__':
    app.run(debug=True)
