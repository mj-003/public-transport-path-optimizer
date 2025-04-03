import pandas as pd
from collections import defaultdict
from src.utils import time_to_minutes
from src.data_structures import TransportStop, TransportConnection

def add_waiting_connections(stops, connections):
    """Dodaje połączenia oczekiwania na przystankach"""
    for stop_name, stop in stops.items():
        departure_times = set()
        for connections_list in stop.connections.values():
            for conn in connections_list:
                departure_times.add(conn.departure_time)
        
        times = sorted(departure_times)
        
        for i in range(len(times) - 1):
            wait_time = times[i+1] - times[i]
            
            wait_connection = TransportConnection(
                line='wait',
                company='wait',
                departure_time=times[i],
                arrival_time=times[i+1],
                start_stop=stop_name,
                end_stop=stop_name,
                start_coords=stop.coordinates,
                end_coords=stop.coordinates
            )
            
            connections.append(wait_connection)
            stop.add_connection(stop_name, wait_connection)


def load_transport_data(csv_file):
    """
    Wczytuje dane transportowe z pliku CSV, eliminuje duplikaty przystanków 
    i tworzy struktury danych z unikalnymi indeksami.
    """
    df = pd.read_csv(csv_file)
    print(f"Wczytano {len(df)} połączeń komunikacyjnych")
    
    df_unique_stops = df[['start_stop', 'start_stop_lat', 'start_stop_lon']].drop_duplicates()
    df_unique_stops['stop_index'] = df_unique_stops.index + 1
    
    df = df.merge(
        df_unique_stops[['start_stop', 'start_stop_lat', 'start_stop_lon', 'stop_index']], 
        on=['start_stop', 'start_stop_lat', 'start_stop_lon'], 
        how='left'
    )
    
    stops = {}  # name -> TransportStop
    connections = []  # lista wszystkich połączeń
    
    for _, row in df.iterrows():
        start_stop = row['start_stop']
        end_stop = row['end_stop']
        departure = time_to_minutes(row['departure_time'])
        arrival = time_to_minutes(row['arrival_time'])
        line = row['line']
        company = row['company']
        
        if start_stop not in stops:
            stops[start_stop] = TransportStop(start_stop)
        
        if end_stop not in stops:
            stops[end_stop] = TransportStop(end_stop)
        
        if pd.notna(row['start_stop_lat']) and pd.notna(row['start_stop_lon']):
            stops[start_stop].coordinates = (row['start_stop_lat'], row['start_stop_lon'])
        
        if pd.notna(row['end_stop_lat']) and pd.notna(row['end_stop_lon']):
            stops[end_stop].coordinates = (row['end_stop_lat'], row['end_stop_lon'])
        
        connection = TransportConnection(
            line=line,
            company=company,
            departure_time=departure,
            arrival_time=arrival,
            start_stop=start_stop,
            end_stop=end_stop,
            start_coords=stops[start_stop].coordinates,
            end_coords=stops[end_stop].coordinates
        )
        
        connections.append(connection)
        stops[start_stop].add_connection(end_stop, connection)
    
    add_waiting_connections(stops, connections)
    
    print(f"Utworzono {len(stops)} przystanków")
    
    return stops, connections