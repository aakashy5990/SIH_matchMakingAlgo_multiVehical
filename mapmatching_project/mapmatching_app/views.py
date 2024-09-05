import pandas as pd
import os
from django.shortcuts import render
from django.http import HttpResponse
from .utils import map_matching, create_map
from .models import RoadSegment

def home(request):
    return render(request, 'mapmatching/home.html')

def upload_view(request):
    if request.method == 'POST':
        gps_file = request.FILES.get('gps_file')
        road_file = request.FILES.get('road_file')
        
        if gps_file and road_file:
            try:
                gps_data = pd.read_csv(gps_file, dtype={'latitude': float, 'longitude': float, 'vehicle_id': int})
                road_segments = pd.read_csv(road_file, dtype={'start_latitude': float, 'start_longitude': float, 'end_latitude': float, 'end_longitude': float})
                
                # Save road segments to the database
                road_segments_records = [
                    RoadSegment(start_latitude=row['start_latitude'], start_longitude=row['start_longitude'],
                                end_latitude=row['end_latitude'], end_longitude=row['end_longitude'], road_type=row['road_type'])
                    for index, row in road_segments.iterrows()
                ]
                RoadSegment.objects.bulk_create(road_segments_records)
                
                # Perform map matching
                matched_segments = map_matching(gps_data, road_segments)
                
                # Generate maps for each vehicle
                maps = []
                vehicle_ids = matched_segments['vehicle_id'].unique()
                
                for vehicle_id in vehicle_ids:
                    map_path = os.path.join('static', f'map_vehicle_{vehicle_id}.html')
                    create_map(matched_segments, vehicle_id, map_path)
                    maps.append({
                        'vehicle_id': vehicle_id,
                        'map_path': f'/static/map_vehicle_{vehicle_id}.html'  # URL for the map file
                    })

                return render(request, 'mapmatching/results.html', {'matched_segments': matched_segments.to_dict(orient='records'), 'maps': maps})
            
            except ValueError as ve:
                return HttpResponse(f"ValueError: {ve}", status=400)
            except KeyError as e:
                return HttpResponse(f"KeyError: {e}", status=400)
        else:
            return HttpResponse("Files are required.", status=400)

    return render(request, 'mapmatching/upload.html')