import heapq
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Set
from src.data_structures import TransportRoute, TransportConnection, TransportStop
from src.utils import time_to_minutes
from math import radians, sin, cos, sqrt, atan2

def astar_bi_criteria(
    stops: Dict[str, 'TransportStop'], 
    start_stop: str, 
    end_stop: str, 
    start_time: str,
    transfer_weight: float = 0.7,  # Waga dla przesiadek (0-1)
    time_weight: float = 0.3,      # Waga dla czasu podróży (0-1)
    transfer_time: int = 3
):
    """
    Zaawansowany algorytm A* uwzględniający jednocześnie dwa kryteria:
    - czas podróży
    - liczbę przesiadek
    
    Parametr transfer_weight określa, jak istotne są przesiadki względem czasu podróży.
    
    Args:
        stops: Słownik przystanków (name -> TransportStop)
        start_stop: Przystanek początkowy
        end_stop: Przystanek końcowy
        start_time: Czas rozpoczęcia podróży w formacie HH:MM:SS
        transfer_weight: Waga dla przesiadek (0-1)
        time_weight: Waga dla czasu podróży (0-1)
        transfer_time: Czas potrzebny na przesiadkę (w minutach)
        
    Returns:
        TransportRoute: Znaleziona trasa
    """
    # if callable(transfer_weight):
    #     raise TypeError("transfer_weight cannot be a function. Please provide a float value between 0 and 1.")
    
    # if callable(time_weight):
    #     raise TypeError("time_weight cannot be a function. Please provide a float value between 0 and 1.")
    
    transfer_weight_float = float(transfer_weight)
    time_weight_float = float(time_weight)
    
    total_weight = transfer_weight_float + time_weight_float
    
    transfer_weight_normalized = transfer_weight_float / total_weight
    time_weight_normalized = time_weight_float / total_weight
    
    # print(f"Szukam trasy z '{start_stop}' do '{end_stop}' od godziny {start_time}")
    # print(f"Wagi: przesiadki={transfer_weight_normalized:.2f}, czas={time_weight_normalized:.2f}")
    
    if start_stop not in stops:
        raise ValueError(f"Przystanek początkowy '{start_stop}' nie istnieje w danych")
    if end_stop not in stops:
        raise ValueError(f"Przystanek końcowy '{end_stop}' nie istnieje w danych")
    
    start_time_minutes = time_to_minutes(start_time)
    target_coords = get_stop_coordinates(end_stop, stops)
    initial_lines = get_lines_from_stop(stops, start_stop, start_time_minutes)
    
    if not initial_lines:
        print(f"Brak połączeń wychodzących z '{start_stop}' po godzinie {start_time}")
        return TransportRoute()
    
    heuristic_cache = {}
    
    coord_cache = {end_stop: target_coords}
    if target_coords:
        coord_cache[end_stop] = target_coords
    
    connection_cache = {}
    
    g_score_time = {}  
    g_score_transfers = {}  
    f_score = {} 
    arrival_times = {}
    previous = {}
    
    open_queue = []
    node_counter = 0
    
    processed = set()
    
    for line in initial_lines:
        node = (start_stop, line)
        g_score_time[node] = 0
        g_score_transfers[node] = 0
        
        h_time = get_cached_time_heuristic(
            start_stop, end_stop, stops, 
            heuristic_cache, coord_cache
        )
        h_transfers = get_cached_transfers_heuristic(
            start_stop, end_stop, stops, 
            heuristic_cache
        )
        
        combined_h = time_weight_normalized * h_time + transfer_weight_normalized * h_transfers * 30
        
        f_score[node] = combined_h
        arrival_times[node] = start_time_minutes
        
        node_counter += 1
        heapq.heappush(open_queue, (combined_h, node_counter, node))
    
    visited_nodes = 0
    start_time_exec = time.time()
    
    best_goal_score = float('inf')
    best_goal_node = None
    
    while open_queue:
        current_f, _, node = heapq.heappop(open_queue)
        current_stop, current_line = node
        
        visited_nodes += 1
        
        if current_f >= best_goal_score:
            continue
        
        if current_stop == end_stop:
            combined_g = (
                time_weight_normalized * g_score_time[node] + 
                transfer_weight_normalized * g_score_transfers[node] * 30
            )
            
            if combined_g < best_goal_score:
                best_goal_score = combined_g
                best_goal_node = node
            continue
        
        if node in processed:
            continue
        
        processed.add(node)
        
        current_time = arrival_times[node]
        
        cache_key = (current_stop, current_line, current_time)
        
        if cache_key not in connection_cache:
            valid_connections = []
            
            for next_stop, connections in stops[current_stop].connections.items():
                earliest_conn = stops[current_stop].get_earliest_connection(
                    next_stop, current_time, current_line, transfer_time
                )
                
                if earliest_conn:
                    valid_connections.append((next_stop, earliest_conn))
            
            connection_cache[cache_key] = valid_connections
        else:
            valid_connections = connection_cache[cache_key]
        
        for next_stop, earliest_conn in valid_connections:
            next_line = earliest_conn.line
            next_node = (next_stop, next_line)
            next_time = earliest_conn.arrival_time
            
            is_transfer = (current_line != next_line) and (current_line != 'wait') and (next_line != 'wait')
            
            new_time = next_time - start_time_minutes
            new_transfers = g_score_transfers.get(node, 0) + (1 if is_transfer else 0)
            
            update_node = False
            
            new_combined_g = (
                time_weight_normalized * new_time + 
                transfer_weight_normalized * new_transfers * 30
            )
            
            if next_node not in g_score_time:
                update_node = True
            else:
                current_combined_g = (
                    time_weight_normalized * g_score_time[next_node] + 
                    transfer_weight_normalized * g_score_transfers[next_node] * 30
                )
                
                if new_combined_g < current_combined_g:
                    update_node = True
            
            if update_node and new_combined_g < best_goal_score:
                g_score_time[next_node] = new_time
                g_score_transfers[next_node] = new_transfers
                arrival_times[next_node] = next_time
                previous[next_node] = (node, earliest_conn)
                
                # Obliczamy heurystykę
                h_time = get_cached_time_heuristic(
                    next_stop, end_stop, stops, 
                    heuristic_cache, coord_cache
                )
                h_transfers = get_cached_transfers_heuristic(
                    next_stop, end_stop, stops, 
                    heuristic_cache
                )
                
                combined_h = time_weight_normalized * h_time + transfer_weight_normalized * h_transfers * 30
                
                next_f = new_combined_g + combined_h
                f_score[next_node] = next_f
                
                if next_f < best_goal_score:
                    node_counter += 1
                    heapq.heappush(open_queue, (next_f, node_counter, next_node))
    
    end_time_exec = time.time()
    execution_time = end_time_exec - start_time_exec
    
    # print(f"Odwiedzono {visited_nodes} węzłów")
    # print(f"Czas wykonania algorytmu: {execution_time:.3f} s")
    
    route = TransportRoute()
    
    goal_node = best_goal_node
    
    if goal_node is None:
        goal_nodes = [(stop, line) for (stop, line) in g_score_time.keys() if stop == end_stop]
        if not goal_nodes:
            print(f"Nie znaleziono trasy z '{start_stop}' do '{end_stop}'")
            return route
        
        goal_node = min(goal_nodes, key=lambda node: (
            time_weight_normalized * g_score_time[node] + 
            transfer_weight_normalized * g_score_transfers[node] * 30
        ))
    
    connections = []
    current_node = goal_node
    
    while current_node in previous:
        prev_node, connection = previous[current_node]
        connections.append(connection)
        current_node = prev_node
    
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
    
    if route.total_time < 0:
        # print(f"Wykryto ujemny czas podróży, prawdopodobnie trasa przechodzi przez północ (00:00)")
        # print(f"Faktyczny czas podróży: {route.total_time + 1440:.1f} min")
        route.total_time += 1440
    
    # if goal_node:
    #     print(f"Znaleziono trasę z {g_score_transfers[goal_node]} przesiadkami, całkowity czas: {route.total_time:.1f} min")
    
    return route

def get_cached_time_heuristic(
    current_stop: str, 
    target_stop: str, 
    stops: Dict[str, 'TransportStop'],
    cache: Dict,
    coord_cache: Dict,
    scale_factor: float = 0.95
) -> float:
    """
    Wersja hierarchical_time_heuristic z cache.
    """
    cache_key = ('time', current_stop, target_stop)
    if cache_key in cache:
        return cache[cache_key]
    
    if current_stop not in coord_cache:
        coord_cache[current_stop] = get_stop_coordinates(current_stop, stops)
    if target_stop not in coord_cache:
        coord_cache[target_stop] = get_stop_coordinates(target_stop, stops)
    
    current_coords = coord_cache[current_stop]
    target_coords = coord_cache[target_stop]
    
    if current_coords and target_coords:
        distance_km = calculate_distance(
            current_coords[0], current_coords[1],
            target_coords[0], target_coords[1]
        ) / 1000
        
        travel_time = distance_km / 0.5
    else:
        travel_time = 30  
    
    direct_connections = False
    for next_stop, connections in stops[current_stop].connections.items():
        if next_stop == target_stop and connections:
            direct_connections = True
            break
    
    if direct_connections:
        travel_time *= 0.8
    
    start_density = len(stops[current_stop].connections)
    try:
        end_density = len(stops[target_stop].connections)
    except KeyError:
        end_density = 0
    
    if start_density > 5 and end_density > 5:
        travel_time *= 0.9
    elif start_density < 3 or end_density < 3:
        travel_time *= 1.1
    
    result = travel_time * scale_factor
    cache[cache_key] = result
    return result


def get_cached_transfers_heuristic(
    current_stop: str, 
    target_stop: str, 
    stops: Dict[str, 'TransportStop'],
    cache: Dict
) -> float:
    """
    Wersja min_transfers_heuristic z cache.
    """
    cache_key = ('transfers', current_stop, target_stop)
    if cache_key in cache:
        return cache[cache_key]
    
    if current_stop == target_stop:
        cache[cache_key] = 0
        return 0
    
    for next_stop, connections in stops[current_stop].connections.items():
        if next_stop == target_stop and connections:
            cache[cache_key] = 0
            return 0
    
    current_lines = set()
    for next_stop, connections in stops[current_stop].connections.items():
        for conn in connections:
            if conn.line != 'wait':
                current_lines.add(conn.line)
    
    target_lines = set()
    try:
        for next_stop, connections in stops[target_stop].connections.items():
            for conn in connections:
                if conn.line != 'wait':
                    target_lines.add(conn.line)
    except KeyError:
        pass
    
    if current_lines & target_lines:
        cache[cache_key] = 1
        return 1
    
    cache[cache_key] = 2
    return 2


def get_lines_from_stop(stops: Dict[str, 'TransportStop'], stop_name: str, current_time: int) -> Set[str]:
    """
    Zwraca zbiór wszystkich linii wychodzących z danego przystanku po podanym czasie.
    """
    lines = set()
    stop = stops.get(stop_name)
    
    if not stop:
        return lines
    
    for next_stop, connections in stop.connections.items():
        for conn in connections:
            if conn.departure_time >= current_time and conn.line != 'wait':
                lines.add(conn.line)
    
    return lines


def get_stop_coordinates(stop_name: str, stops: Dict[str, 'TransportStop']) -> Optional[Tuple[float, float]]:
    """
    Pobiera współrzędne przystanku.
    """
    stop = stops.get(stop_name)
    if not stop:
        return None
    
    if stop.coordinates:
        return stop.coordinates
    
    for next_stop, connections in stop.connections.items():
        if connections:
            conn = connections[0]
            if hasattr(conn, 'start_coords') and conn.start_coords:
                return conn.start_coords
    
    return None


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Oblicza odległość między dwoma punktami na Ziemi.
    Używa wzoru haversine do obliczenia odległości na sferze.
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = 6371000 * c  
    
    return distance