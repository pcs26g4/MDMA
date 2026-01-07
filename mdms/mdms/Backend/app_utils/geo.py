import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in meters.
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371000 # Radius of earth in meters
    return c * r

def group_by_location(items, distance_threshold=20):
    """
    Group items by GPS coordinates.
    items: List of dicts, each containing 'latitude' and 'longitude'.
    distance_threshold: distance in meters.
    """
    groups = []
    for item in items:
        found_group = False
        for group in groups:
            # Check against the first item in the group (the 'representative' location)
            dist = calculate_distance(
                item['latitude'], item['longitude'],
                group[0]['latitude'], group[0]['longitude']
            )
            if dist <= distance_threshold:
                group.append(item)
                found_group = True
                break
        
        if not found_group:
            groups.append([item])
    
    return groups
