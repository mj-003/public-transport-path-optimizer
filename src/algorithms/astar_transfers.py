import heapq
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from src.data_structures import TransportRoute, TransportConnection, TransportStop
from src.utils import time_to_minutes, minutes_to_time

def astar_min_transfers(
    stops: Dict[str, 'TransportStop'], 
    start_stop: str, 
    end_stop: str, 
    start_time: str,
    transfer_time: int = 3
):
    """
    Znajduje trasę z minimalną liczbą przesiadek algorytmem A*.
    Czas podróży jest ignorowany - ważna jest tylko minimalizacja przesiadek.
    
    Args:
        stops: Słownik przystanków (name -> TransportStop)
        start_stop: Przystanek początkowy
        end_stop: Przystanek końcowy
        start_time: Czas rozpoczęcia podróży w formacie HH:MM:SS
        transfer_time: Czas potrzebny na przesiadkę (w minutach)
        
    Returns:
        TransportRoute: Znaleziona trasa
    """
    print(f"Szukam trasy z '{start_stop}' do '{end_stop}' od godziny {start_time} z minimalną liczbą przesiadek")
    
    if start_stop not in stops:
        raise ValueError(f"Przystanek początkowy '{start_stop}' nie istnieje w danych")
    if end_stop not in stops:
        raise ValueError(f"Przystanek końcowy '{end_stop}' nie istnieje w danych")
    
    start_time_minutes = time_to_minutes(start_time)
    
    transfers_count = {}    
    arrival_times = {}      
    previous = {}           
    
    transfers_count[(start_stop, None)] = 0
    arrival_times[(start_stop, None)] = start_time_minutes
    
    entry_count = 0
    priority_queue = [(0, heuristic(start_stop, end_stop, stops), entry_count, start_stop, None)]    
    closed_set = set()    
    visited_nodes = 0
    
    while priority_queue:
        current_transfers, _, _, current_stop, current_line = heapq.heappop(priority_queue)
        current_key = (current_stop, current_line)
        
        if current_stop == end_stop:
            # print(f"Znaleziono trasę do '{end_stop}' z {current_transfers} przesiadkami!")
            break
        
        if current_key in closed_set:
            continue
        
        closed_set.add(current_key)
        visited_nodes += 1
        
        current_time = arrival_times[current_key]
        
        for next_stop, connections_list in stops[current_stop].connections.items():
            if current_line:
                same_line_connections = []
                for conn in connections_list:
                    if conn.departure_time >= current_time and conn.line == current_line:
                        same_line_connections.append(conn)
                
                if same_line_connections:
                    same_line_connections.sort(key=lambda x: x.departure_time)
                    earliest_conn = same_line_connections[0]
                    
                    new_transfers = current_transfers
                    new_key = (next_stop, earliest_conn.line)
                    
                    if new_key not in transfers_count or new_transfers < transfers_count[new_key]:
                        transfers_count[new_key] = new_transfers
                        arrival_times[new_key] = earliest_conn.arrival_time
                        previous[new_key] = (current_key, earliest_conn)
                        
                        if new_key not in closed_set:
                            entry_count += 1
                            h = heuristic(next_stop, end_stop, stops)
                            heapq.heappush(priority_queue, (
                                new_transfers,
                                h,
                                entry_count,
                                next_stop,
                                earliest_conn.line
                            ))
            
            valid_connections = []
            for conn in connections_list:
                if conn.line == 'wait':
                    continue
                    
                if conn.departure_time >= current_time:
                    if current_line and conn.line != current_line:
                        if conn.departure_time >= current_time + transfer_time:
                            valid_connections.append(conn)
                    else:
                        valid_connections.append(conn)
            
            valid_connections.sort(key=lambda x: x.departure_time)
            
            for conn in valid_connections:
                is_transfer = current_line and conn.line != current_line
                new_transfers = current_transfers + (1 if is_transfer else 0)
                
                new_key = (next_stop, conn.line)
                
                if new_key not in transfers_count or new_transfers < transfers_count[new_key]:
                    transfers_count[new_key] = new_transfers
                    arrival_times[new_key] = conn.arrival_time
                    previous[new_key] = (current_key, conn)
                    
                    if new_key not in closed_set:
                        entry_count += 1
                        h = heuristic(next_stop, end_stop, stops)
                        heapq.heappush(priority_queue, (
                            new_transfers,
                            h,
                            entry_count,
                            next_stop,
                            conn.line
                        ))
    
    # print(f"Odwiedzono {visited_nodes} węzłów")
    
    best_path = None
    min_transfers = float('inf')
    
    for key, count in transfers_count.items():
        stop, line = key
        if stop == end_stop and count < min_transfers:
            min_transfers = count
            best_path = key
    
    if best_path is None:
        print(f"Nie znaleziono trasy z '{start_stop}' do '{end_stop}'")
        return TransportRoute()
    
    route = TransportRoute()
    connections = []
    current_key = best_path
    
    while current_key in previous:
        prev_key, connection = previous[current_key]
        connections.append(connection)
        current_key = prev_key
    
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
    
    # if route.total_time < 0:
    #     # Dodajemy 24 godziny (1440 minut) dla tras przechodzących przez północ
    #     # To poprawia wyświetlanie czasu, nie wpływając na faktyczną trasę
    #     print(f"Wykryto ujemny czas podróży, prawdopodobnie trasa przechodzi przez północ (00:00)")
    #     print(f"Faktyczny czas podróży: {route.total_time + 1440:.1f} min")
    # else:
    #     print(f"Znaleziono trasę z {min_transfers} przesiadkami, całkowity czas: {route.total_time:.1f} min")
    
    return route


def heuristic(current_stop: str, target_stop: str, stops: Dict[str, 'TransportStop']) -> float:
    """
    Prosta heurystyka dla A* - zwraca 0 dla każdego przypadku.
    Można zastąpić bardziej zaawansowaną heurystyką, jeśli potrzeba.
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