import heapq
from collections import defaultdict
from src.utils import time_to_minutes
from src.data_structures import TransportRoute, TransportConnection

def dijkstra_shortest_path(stops, start_stop, end_stop, start_time, transfer_time=3):
    """
    Znajduje najkrótszą trasę algorytmem Dijkstry.
    
    Args:
        stops: Słownik przystanków (name -> TransportStop)
        start_stop: Przystanek początkowy
        end_stop: Przystanek końcowy
        start_time: Czas rozpoczęcia podróży w formacie HH:MM:SS
        transfer_time: Czas potrzebny na przesiadkę (w minutach)
        
    Returns:
        TransportRoute: Znaleziona trasa
    """
    # print(f"Szukam trasy z '{start_stop}' do '{end_stop}' algorytmem Dijkstry")
    # print(f"Szukam trasy z '{start_stop}' do '{end_stop}' od godziny {start_time}")
    
    if start_stop not in stops:
        raise ValueError(f"Przystanek początkowy '{start_stop}' nie istnieje w danych")
    if end_stop not in stops:
        raise ValueError(f"Przystanek końcowy '{end_stop}' nie istnieje w danych")
    
    start_time_minutes = time_to_minutes(start_time)
    
    best_arrival_time = defaultdict(lambda: float('inf'))
    best_arrival_time[start_stop] = start_time_minutes
    
    distances = defaultdict(lambda: float('inf'))
    previous = {}
    previous_lines = {}
    
    distances[(start_stop, start_time_minutes)] = 0
    previous_lines[(start_stop, start_time_minutes)] = None
    
    pq = [(0, (start_stop, start_time_minutes))]
    
    visited_nodes = 0
    found_end = False
    
    while pq and not found_end:
        current_dist, current = heapq.heappop(pq)
        visited_nodes += 1
        
        current_stop, current_time = current
        current_line = previous_lines.get(current, None)
        
        if current_stop == end_stop:
            found_end = True
            break
        
        if current_time > best_arrival_time[current_stop]:
            continue
            
        if current_dist > distances[current]:
            continue
        
        for next_stop, connections_list in stops[current_stop].connections.items():

            if current_time >= best_arrival_time[next_stop]:
                continue
                
            earliest_conn = stops[current_stop].get_earliest_connection(
                next_stop, current_time, current_line, transfer_time
            )
            
            if earliest_conn:
                next_node = (next_stop, earliest_conn.arrival_time)
                
                new_dist = current_dist + (earliest_conn.arrival_time - current_time)
                
                if new_dist < distances[next_node]:
                    distances[next_node] = new_dist
                    previous[next_node] = (current, earliest_conn)
                    previous_lines[next_node] = earliest_conn.line
                    
                    if earliest_conn.arrival_time < best_arrival_time[next_stop]:
                        best_arrival_time[next_stop] = earliest_conn.arrival_time
                        heapq.heappush(pq, (new_dist, next_node))
    
    # print(f"Odwiedzono {visited_nodes} węzłów grafu")
    
    route = TransportRoute()
    
    if found_end:
        target_times = [(time, dist) for (stop, time), dist in distances.items() if stop == end_stop]
        if target_times:
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
            
            # print(f"Znaleziono trasę, całkowity czas: {route.total_time:.1f} min, przesiadki: {route.transfers}")
    else:
        print(f"Nie znaleziono ścieżki z '{start_stop}' do '{end_stop}'")
    
    return route