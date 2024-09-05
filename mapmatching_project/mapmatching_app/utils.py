import pandas as pd
from sklearn.neighbors import BallTree
from geopy.geocoders import Nominatim
import folium
import os
import requests
import logging
from django.conf import settings
from branca.element import Template, MacroElement


def map_matching(gps_data: pd.DataFrame, road_segments: pd.DataFrame):
    required_columns = ['start_latitude', 'start_longitude', 'end_latitude', 'end_longitude']
    
    for col in required_columns:
        if col not in road_segments.columns:
            raise KeyError(f"Required column '{col}' not found in road_segments")

    road_array = road_segments[['start_latitude', 'start_longitude', 'end_latitude', 'end_longitude']].to_numpy()
    tree = BallTree(road_array[:, :2])  # Use start_latitude and start_longitude for querying
    
    matched_segments = []
    geolocator = Nominatim(user_agent="map-matching")

    for index, gps_row in gps_data.iterrows():
        gps_lat = gps_row['latitude']
        gps_lon = gps_row['longitude']
        vehicle_id = gps_row['vehicle_id']  # Get vehicle ID

        dist, ind = tree.query([[gps_lat, gps_lon]], k=1)
        nearest_segment = road_segments.iloc[ind[0][0]]
        
        # Reverse geocode to get location name
        location = geolocator.reverse((gps_lat, gps_lon), exactly_one=True)
        address = location.raw.get('address', {})
        city = address.get('city', '')
        state = address.get('state', '')
        country = address.get('country', '')

        matched_segments.append({
            'vehicle_id': vehicle_id,
            'gps_lat': gps_lat,
            'gps_lon': gps_lon,
            'start_lat': nearest_segment['start_latitude'],
            'start_lon': nearest_segment['start_longitude'],
            'end_lat': nearest_segment['end_latitude'],
            'end_lon': nearest_segment['end_longitude'],
            'city': city,
            'state': state,
            'country': country
        })
    
    matched_segments_df = pd.DataFrame(matched_segments)
    return matched_segments_df

def reverse_geocode(lat, lon):
    api_key = 'b0534b2739234881ba860d54a6b4db19'  # Replace with your OpenCage API key
    url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    
    if data['results']:
        components = data['results'][0]['components']
        city = components.get('city', 'Unknown')
        state = components.get('state', 'Unknown')
        normalized_city = components.get('_normalized_city', 'Unknown')
        return city, state, normalized_city
    else:
        return None, None, None
    
def create_map(matched_segments: pd.DataFrame, vehicle_id: int, map_path: str):
    # Create a folium map centered around the first GPS point
    start_lat = matched_segments.iloc[0]['gps_lat']
    start_lon = matched_segments.iloc[0]['gps_lon']
    folium_map = folium.Map(location=[start_lat, start_lon], zoom_start=13)
    
    # Add road segments to the map
    for _, row in matched_segments.iterrows():
        folium.PolyLine(
            locations=[(row['start_lat'], row['start_lon']), (row['end_lat'], row['end_lon'])],
            color='blue',
            weight=2.5,
            opacity=1
        ).add_to(folium_map)
    
    # Save the map as an HTML file
    folium_map.save(map_path)