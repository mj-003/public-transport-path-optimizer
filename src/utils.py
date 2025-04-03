import math

def time_to_minutes(time_str):
    """Konwersja czasu HH:MM:SS na minuty od północy"""
    hours, minutes, seconds = map(int, time_str.split(':'))
    if hours >= 24:  
        hours %= 24
    return hours * 60 + minutes + seconds / 60

def minutes_to_time(minutes):
    """Konwersja minut z powrotem na format HH:MM:SS"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    secs = int((minutes % 1) * 60)
    
    if hours >= 24:
        hours %= 24
    return f"{hours:02d}:{mins:02d}:{secs:02d}"

def calculate_distance(coords1, coords2):
    """Oblicza odległość geograficzną między dwoma punktami (w km)"""
    if not coords1 or not coords2:
        return 0
    
    lat1, lon1 = coords1
    lat2, lon2 = coords2
    
    # Promień Ziemi w km
    R = 6371.0
    
    # Konwersja do radianów
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Różnica długości i szerokości geograficznej
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    # Wzór haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance

def estimate_travel_time(stop1, stop2, stops):
    """
    Heurystyka dla A* - szacowany czas podróży między przystankami.
    Zakłada średnią prędkość transportu miejskiego 25 km/h.
    """
    if stop1 not in stops or stop2 not in stops:
        return 0
    
    coords1 = stops[stop1].coordinates
    coords2 = stops[stop2].coordinates
    
    if not coords1 or not coords2:
        return 0
    
    distance = calculate_distance(coords1, coords2)
    
    # Szacowanie czasu podróży (w minutach)
    travel_time_estimate = distance / 0.417
    
    return travel_time_estimate * 0.9 