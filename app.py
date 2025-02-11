#!/usr/bin/python3
'''
Created on 11-02-2025

@author: Kyllian Cuevas & Thomas Mirbey
@version: 1

Python Website for 5G NR antenna configuration using FLASK for Master IOT project
'''

#------------------
# Import
#------------------

from flask import Flask, request, render_template, redirect, url_for
import math
import requests
import concurrent.futures

#------------------
# Functions
#------------------

app = Flask(__name__)
API_URL = "https://api.open-meteo.com/v1/forecast"

def get_average_speed(lat, lon):
    '''
    returns the average speed of all the roads in a radius of 2km

    lat : latitude in float
    lon : longitude in float
    '''
    overpass_url = "http://overpass-api.de/api/interpreter"
    earth_radius = 6371
    zone_radius = 2
    lat_offset = (zone_radius / earth_radius) * (180 / math.pi)
    lon_offset = lat_offset / math.cos(math.radians(lat))
    # define a zone of 2 km arround the selected position
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
        # parse response to json and compute the average speed
        data = response.json()
        for element in data["elements"]:
            if 'maxspeed' in element.get('tags', {}):
                try:
                    # some US roads have speed as X mph instead of X
                    # so remove mph before converting to int
                    if ' mph' in element['tags']['maxspeed']:
                        element['tags']['maxspeed'].replace(' mph','')
                    av_speed += int(element['tags']['maxspeed'])
                    av_element += 1
                except ValueError:
                    # tag is not an int
                    pass

    # if average speed was computed, return it, otherwhise return 0
    return av_speed / av_element if av_element > 1 else 0

def get_building_density(lat, lon):
    '''
    returns the amount of building in a 2km radius

    lat : latitude in float
    lon : longitude in float
    '''
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
    #print(f'coords: {lat},{lon}')

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

        if int(building_count) > 10000:
            print("This is a dense area")
        else:
            print("This area is not very dense")
        return int(building_count)
    else:
        print("Error fetching data:", response.status_code)
        return 0


def get_land_type(lat, lon):
    '''
    returns the land type of the zone, might return unknown depending on the specific zone

    lat : latitude in float
    lon : longitude in float
    '''
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
    '''
    returns if there are moutains nearby (True/False)

    lat : latitude in float
    lon : longitude in float
    '''
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    node(around:{radius * 1000},{lat},{lon})["natural"="peak"];
    out;
    """
    response = requests.get(overpass_url, params={"data": overpass_query})
    # if there are more than 5 elements in the response, we consider the place to have mountains, otherwhise not
    return len(response.json().get("elements", [])) > 5 if response.status_code == 200 else False

def get_elevation(lat, lon):
    '''
    returns the average elevation of the zone. Might not return anything depending on the selected zone
    and the frequency of the api calls

    lat : latitude in float
    lon : longitude in float
    '''
    response = requests.get(f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}")
    return response.json().get("results", [{}])[0].get("elevation", 0) if response.status_code == 200 else 0

def calculate_5g_antenna_config(building_density, land_type, mountains, elevation, avg_speed):
    '''
    returns 5g antenna configuration based on the values retrieved by the api call

    lat : latitude in float
    lon : longitude in float
    '''
    if mountains:
        return {"Frequency": "3.5 GHz", "Subcarrier Size": "30 kHz", "Cyclic Prefix Mode": "Extended", "Output Power": "High", "Coverage Radius": "1.5 km"}
    elif avg_speed > 80:
        return {"Frequency": "700 MHz", "Subcarrier Size": "15 kHz", "Cyclic Prefix Mode": "Extended", "Output Power": "High", "Coverage Radius": "10 km"}
    elif building_density > 500:
        return {"Frequency": "26 GHz", "Subcarrier Size": "120 kHz", "Cyclic Prefix Mode": "Normal", "Output Power": "Medium", "Coverage Radius": "0.5 km"}
    elif building_density > 100:
        return {"Frequency": "3.5 GHz", "Subcarrier Size": "30 kHz", "Cyclic Prefix Mode": "Normal", "Output Power": "Medium", "Coverage Radius": "2 km"}
    else:
        return {"Frequency": "700 MHz", "Subcarrier Size": "15 kHz", "Cyclic Prefix Mode": "Extended", "Output Power": "Low", "Coverage Radius": "10 km"}

#------------------
# API
#------------------

@app.route('/')
def home():
    '''
    main endpoint for selecting a position
    '''
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    '''
    page to show the 5g antenna configuration to the user
    based on the selected coordinates
    '''
    lat, lon = request.form['lat'], request.form['lon']
    try:
        # if not coordinates were selected, we get ''
        # so we return to the coordinate selection page
        lat, lon = float(lat), float(lon)
    except ValueError:
        return redirect(url_for('home'))
    
    # execute api call simultaneously but wait for all results
    # to go further in the execution
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_building_density = executor.submit(get_building_density, lat, lon)
        future_land_type = executor.submit(get_land_type, lat, lon)
        future_mountains = executor.submit(get_mountains_nearby, lat, lon)
        future_elevation = executor.submit(get_elevation, lat, lon)
        future_avg_speed = executor.submit(get_average_speed, lat, lon)
        
        building_density = future_building_density.result()
        land_type = future_land_type.result()
        mountains = future_mountains.result()
        elevation = future_elevation.result()
        avg_speed = future_avg_speed.result()
    
    antenna_config = calculate_5g_antenna_config(building_density, land_type, mountains, elevation, avg_speed)
    return render_template('result.html', lat=lat, lon=lon, building_density=building_density, 
                           land_type=land_type, mountains=mountains, elevation=elevation, 
                           avg_speed=int(avg_speed), antenna_config=antenna_config)

#------------------
# Main
#------------------

if __name__ == '__main__':
    '''
    Starts the server on port 8080 accessible to all clients (0.0.0.0)
    '''
    app.run(debug=True, port=8080, host="0.0.0.0")

