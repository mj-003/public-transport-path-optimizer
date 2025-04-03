import heapq
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple
from src.data_structures import TransportRoute, TransportConnection, TransportStop
from src.utils import time_to_minutes


def astar_shortest_path(
    stops: Dict[str, 'TransportStop'], 
    start_stop: str, 
    end_stop: str, 
    start_time: str,
    heuristic_func: Callable[[str, str, Dict[str, 'TransportStop'], Optional[str], bool], float] = None,
    transfer_time: int = 3
):
    """
    Znajduje najkrótszą trasę algorytmem A* z konfigurowalnymi heurystykami.
    
    Args:
        stops: Słownik przystanków (name -> TransportStop)
        start_stop: Przystanek początkowy
        end_stop: Przystanek końcowy
        start_time: Czas rozpoczęcia podróży w formacie HH:MM:SS
        heuristic_func: Funkcja heurystyczna do obliczania szacowanego kosztu (domyślnie zero_heuristic)
        transfer_time: Czas potrzebny na przesiadkę (w minutach)
        
    Returns:
        TransportRoute: Znaleziona trasa
    """
    # print(f"Szukam trasy z '{start_stop}' do '{end_stop}' algorytmem A*")
    # print(f"Szukam trasy z '{start_stop}' do '{end_stop}' od godziny {start_time}")
    
    if heuristic_func is None:
        heuristic_func = zero_heuristic
    
    if start_stop not in stops:
        raise ValueError(f"Przystanek początkowy '{start_stop}' nie istnieje w danych")
    if end_stop not in stops:
        raise ValueError(f"Przystanek końcowy '{end_stop}' nie istnieje w danych")
    
    end_coords = get_stop_coordinates(end_stop, stops)
    
    start_time_minutes = time_to_minutes(start_time)
    
    best_arrival_time = defaultdict(lambda: float('inf'))
    best_arrival_time[start_stop] = start_time_minutes
    
    g_score = defaultdict(lambda: float('inf'))  
    f_score = defaultdict(lambda: float('inf')) 
    
    previous = {}  
    previous_lines = {}  
    
    g_score[(start_stop, start_time_minutes)] = 0
    
    h_start = heuristic_func(start_stop, end_stop, stops, None, False)
    f_score[(start_stop, start_time_minutes)] = h_start
    previous_lines[(start_stop, start_time_minutes)] = None
    
    counter = 0
    
    open_set = [(f_score[(start_stop, start_time_minutes)], counter, (start_stop, start_time_minutes))]
    counter += 1
    
    open_set_entries = {(start_stop, start_time_minutes)}
    
    visited_nodes = 0
    
    best_target_score = float('inf')
    best_target_node = None
    
    heuristic_cache = {}
    
    def cached_heuristic(curr, target, stops_dict, prev=None, is_transfer=False):
        key = (curr, target, prev, is_transfer)
        if key not in heuristic_cache:
            heuristic_cache[key] = heuristic_func(curr, target, stops_dict, prev, is_transfer)
        return heuristic_cache[key]
    
    while open_set:
        _, _, current = heapq.heappop(open_set)
        open_set_entries.remove(current)
        visited_nodes += 1
        
        current_stop, current_time = current
        current_line = previous_lines.get(current, None)
        
        if current_stop == end_stop:
            best_target_node = current
            best_target_score = g_score[current]
            break
        
        if current_time > best_arrival_time[current_stop]:
            continue
            
        current_g = g_score[current]
        if current_g + cached_heuristic(current_stop, end_stop, stops, None, False) >= best_target_score:
            continue
        
        for next_stop in stops[current_stop].connections:
            if best_arrival_time[next_stop] <= current_time:
                continue
                
            earliest_conn = stops[current_stop].get_earliest_connection(
                next_stop, current_time, current_line, transfer_time
            )
            
            if earliest_conn:
                is_transfer = current_line is not None and current_line != 'wait' and current_line != earliest_conn.line
                next_node = (next_stop, earliest_conn.arrival_time)
                tentative_g_score = current_g + (earliest_conn.arrival_time - current_time)
                
                if tentative_g_score >= g_score[next_node]:
                    continue
                
                if earliest_conn.arrival_time < best_arrival_time[next_stop]:
                    best_arrival_time[next_stop] = earliest_conn.arrival_time
                
                previous[next_node] = (current, earliest_conn)
                g_score[next_node] = tentative_g_score
                
                h_score = cached_heuristic(next_stop, end_stop, stops, current_stop, is_transfer)
                next_f = tentative_g_score + h_score
                f_score[next_node] = next_f
                previous_lines[next_node] = earliest_conn.line
                
                if next_stop == end_stop and tentative_g_score < best_target_score:
                    best_target_score = tentative_g_score
                    best_target_node = next_node
                
                if next_node not in open_set_entries:
                    heapq.heappush(open_set, (next_f, counter, next_node))
                    counter += 1
                    open_set_entries.add(next_node)
    
    # print(f"Odwiedzono {visited_nodes} węzłów grafu")
    
    route = TransportRoute()
    
    current = best_target_node
    
    if not current:
        target_times = [(time, score) for (stop, time), score in g_score.items() if stop == end_stop]
        
        if not target_times:
            print(f"Nie znaleziono ścieżki z '{start_stop}' do '{end_stop}'")
            return route
        
        target_time = min(target_times, key=lambda x: x[1])[0]
        current = (end_stop, target_time)
    
    connections = []
    while current in previous:
        prev_node, connection = previous[current]
        connections.append(connection)
        current = prev_node
    
    connections.reverse()
    
    previous_connection = None
    for connection in connections:
        if previous_connection is not None:
            if (previous_connection.end_stop == connection.start_stop and 
                previous_connection.arrival_time < connection.departure_time):
                wait_connection = TransportConnection(
                    line='wait',
                    company='wait',
                    departure_time=previous_connection.arrival_time,
                    arrival_time=connection.departure_time,
                    start_stop=previous_connection.end_stop,
                    end_stop=connection.start_stop,
                    start_coords=None,
                    end_coords=None
                )
                route.add_connection(wait_connection)
        
        route.add_connection(connection)
        previous_connection = connection
    
    route.calculate_stats(start_time=start_time)
    
    # print(f"Znaleziono trasę algorytmem A*, całkowity czas: {route.total_time:.1f} min, przesiadki: {route.transfers}")
    
    return route



def zero_heuristic(
    current_stop: str, 
    target_stop: str, 
    stops: Dict[str, 'TransportStop'], 
    previous_stop: Optional[str] = None,
    is_transfer: bool = False
) -> float:
    """
    Heurystyka zerowa - zawsze zwraca 0.
    W praktyce przekształca A* w algorytm Dijkstry.
    """
    return 0


def get_stop_coordinates(stop_name: str, stops: Dict[str, 'TransportStop']) -> Optional[Tuple[float, float]]:
    """
    Pomocnicza funkcja do pobierania współrzędnych przystanku.
    """
    stop = stops.get(stop_name)
    if not stop:
        return None
    
    if stop.coordinates:
        return stop.coordinates
    
    for next_stop, connections in stop.connections.items():
        if connections:
            conn = connections[0]
            if conn.start_coords:
                return conn.start_coords
    
    return None


def distance_heuristic(
    current_stop: str, 
    target_stop: str, 
    stops: Dict[str, 'TransportStop'], 
    previous_stop: Optional[str] = None,
    is_transfer: bool = False
) -> float:
    """
    Heurystyka oparta na odległości euklidesowej między przystankami.
    Szacuje czas podróży zakładając średnią prędkość 40 km/h.
    
    Przyjmuje współczynnik 0.9 by nie przeszacować (heurystyka musi być dopuszczalna).
    """
    from math import sqrt, cos, radians
    
    current_coords = get_stop_coordinates(current_stop, stops)
    target_coords = get_stop_coordinates(target_stop, stops)
    
    if not current_coords or not target_coords:
        return 0
    
    current_lat, current_lon = current_coords
    target_lat, target_lon = target_coords
    
    dx = 111.32 * abs(current_lon - target_lon) * cos(radians((current_lat + target_lat)/2))
    dy = 110.574 * abs(current_lat - target_lat)
    distance_km = sqrt(dx**2 + dy**2)
    
    estimated_time = distance_km / 0.5
    
    return estimated_time * 0.9


def transfer_penalty_heuristic(
    current_stop: str, 
    target_stop: str, 
    stops: Dict[str, 'TransportStop'], 
    previous_stop: Optional[str] = None,
    is_transfer: bool = False
) -> float:
    """
    Heurystyka, która karze za przesiadki, zachęcając algorytm do preferowania
    tras z mniejszą liczbą przesiadek.
    """
    base_estimate = distance_heuristic(current_stop, target_stop, stops, previous_stop, is_transfer)
    transfer_penalty = 5.0 if is_transfer else 0.0
    
    return base_estimate + transfer_penalty


def direct_line_preference_heuristic(
    current_stop: str, 
    target_stop: str, 
    stops: Dict[str, 'TransportStop'], 
    previous_stop: Optional[str] = None,
    is_transfer: bool = False
) -> float:
    """
    Heurystyka preferująca trasy bezpośrednie do celu.
    Sprawdza, czy istnieje bezpośrednie połączenie z bieżącego przystanku do celu.
    """
    base_estimate = distance_heuristic(current_stop, target_stop, stops, previous_stop, is_transfer)
    direct_connection_exists = target_stop in stops[current_stop].connections
    direct_connection_bonus = -10.0 if direct_connection_exists else 0.0
    transfer_penalty = 7.0 if is_transfer else 0.0
    
    return base_estimate + transfer_penalty + direct_connection_bonus


def combined_heuristic(
    current_stop: str, 
    target_stop: str, 
    stops: Dict[str, 'TransportStop'], 
    previous_stop: Optional[str] = None,
    is_transfer: bool = False
) -> float:
    """
    Zaawansowana heurystyka łącząca kilka czynników:
    1. Odległość geograficzną
    2. Kary za przesiadki
    3. Kary za ruch w złym kierunku
    """
    from math import sqrt
    
    base_estimate = distance_heuristic(current_stop, target_stop, stops, previous_stop, is_transfer)
    transfer_penalty = 3.0 if is_transfer else 0.0
    
    direction_penalty = 0.0
    if previous_stop:
        prev_coords = get_stop_coordinates(previous_stop, stops)
        curr_coords = get_stop_coordinates(current_stop, stops)
        target_coords = get_stop_coordinates(target_stop, stops)
        
        if prev_coords and curr_coords and target_coords:
            def calc_distance(coord1, coord2):
                lat1, lon1 = coord1
                lat2, lon2 = coord2
                return sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)
            
            prev_to_target = calc_distance(prev_coords, target_coords)
            curr_to_target = calc_distance(curr_coords, target_coords)
            
            if curr_to_target > prev_to_target:
                direction_penalty = 2.0
    
    return base_estimate + transfer_penalty + direction_penalty