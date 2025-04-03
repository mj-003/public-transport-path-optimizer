import folium
from src.utils import minutes_to_time
from typing import List
from prettytable import PrettyTable
from src.utils import minutes_to_time

def format_route(route):
    """Formatuje trasę do czytelnej postaci"""
    if not route.connections:
        return "Nie znaleziono trasy"
    
    result = []
    result.append("📋 HARMONOGRAM PODRÓŻY:")
    
    segments = route.get_segments()
    
    for i, segment in enumerate(segments):
        line = segment['line']
        start_stop = segment['start_stop']
        end_stop = segment['end_stop']
        departure = segment['departure_time']
        arrival = segment['arrival_time']
        
        result.append(f"\n🚍 Linia {line}: {start_stop} → {end_stop}")
        result.append(f"   Odjazd: {minutes_to_time(departure)}, przyjazd: {minutes_to_time(arrival)}")
        
        if len(segment['connections']) > 1:
            result.append("   Przystanki pośrednie:")
            for j, conn in enumerate(segment['connections']):
                if j == 0:  
                    result.append(f"     • {conn.start_stop} ({minutes_to_time(conn.departure_time)})")
                if j < len(segment['connections']) - 1:
                    result.append(f"     • {conn.end_stop} ({minutes_to_time(conn.arrival_time)})")
                    result.append(f"     • {conn.end_stop} ({minutes_to_time(conn.arrival_time)}) [końcowy]")
        
        if i < len(segments) - 1:
            next_segment = segments[i+1]
            wait_time = next_segment['departure_time'] - arrival
            
            result.append(f"\n🔄 Przesiadka: {end_stop}")
            result.append(f"   Czas oczekiwania: {wait_time:.1f} min ({minutes_to_time(arrival)} → {minutes_to_time(next_segment['departure_time'])})")
    
    result.append("\n📊 PODSUMOWANIE:")
    result.append(f"⏱️ Całkowity czas podróży: {route.total_time:.1f} min")
    result.append(f"🔄 Liczba przesiadek: {max(0, route.transfers)}")
    
    return "\n".join(result)

def visualize_route(route, stops, route_title=None):
    """Wizualizacja trasy na mapie przy użyciu Folium"""
    if not route.connections:
        print("Brak danych do wizualizacji")
        return None
    
    segments = route.get_segments()
    
    stops_on_route = []
    for segment in segments:
        for conn in segment['connections']:
            stops_on_route.append(conn.start_stop)
            stops_on_route.append(conn.end_stop)
    
    stops_on_route = list(dict.fromkeys(stops_on_route))
    
    stop_coords = {}
    for stop_name in stops_on_route:
        if stop_name in stops and stops[stop_name].coordinates:
            stop_coords[stop_name] = stops[stop_name].coordinates
    
    if len(stop_coords) < 2:
        print("Brak wystarczającej liczby współrzędnych dla przystanków na trasie")
        return None
    
    coords = list(stop_coords.values())
    center_lat = sum(lat for lat, _ in coords) / len(coords)
    center_lon = sum(lon for _, lon in coords) / len(coords)
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles='CartoDB positron')
    
    if route_title:
        title_html = f'''
            <h3 align="center" style="font-size:16px"><b>{route_title}</b></h3>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
    
    if route.connections:
        start_stop = route.connections[0].start_stop
        end_stop = route.connections[-1].end_stop
        
        if start_stop in stop_coords:
            folium.Marker(
                location=stop_coords[start_stop],
                popup=f"<b>Start:</b> {start_stop}",
                icon=folium.Icon(icon="play", prefix="fa", color="green")
            ).add_to(m)
        
        if end_stop in stop_coords:
            folium.Marker(
                location=stop_coords[end_stop],
                popup=f"<b>Koniec:</b> {end_stop}",
                icon=folium.Icon(icon="stop", prefix="fa", color="red")
            ).add_to(m)
    
    transfer_stops = set()
    prev_line = None
    for conn in route.connections:
        if conn.line != 'wait':
            if prev_line and prev_line != conn.line:
                transfer_stops.add(conn.start_stop)
            prev_line = conn.line
    
    for stop in transfer_stops:
        if stop in stop_coords:
            folium.Marker(
                location=stop_coords[stop],
                popup=f"<b>Przesiadka:</b> {stop}",
                icon=folium.Icon(icon="exchange", prefix="fa", color="orange")
            ).add_to(m)
    
    for stop in stops_on_route:
        if stop not in transfer_stops and stop != start_stop and stop != end_stop and stop in stop_coords:
            folium.Marker(
                location=stop_coords[stop],
                popup=stop,
                icon=folium.Icon(icon="bus", prefix="fa", color="blue")
            ).add_to(m)
    
    colors = ['#e6194B', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#f032e6', '#008080', '#9A6324']
    
    for i, segment in enumerate(segments):
        color = colors[i % len(colors)]
        
        for j in range(len(segment['connections'])):
            conn = segment['connections'][j]
            
            if conn.start_stop in stop_coords and conn.end_stop in stop_coords:
                start_coords = stop_coords[conn.start_stop]
                end_coords = stop_coords[conn.end_stop]
                
                folium.PolyLine(
                    locations=[start_coords, end_coords],
                    color=color,
                    weight=4,
                    opacity=0.8,
                    popup=f"Linia {conn.line}: {conn.start_stop} → {conn.end_stop}"
                ).add_to(m)
    
    return m


def format_compact_route(route):
    """Formatuje trasę do zwięzłej postaci z tabelą najważniejszych informacji"""
    if not route.connections:
        return "Nie znaleziono trasy"
    
    route.calculate_stats()
    
    summary = [
        f"⏱️ Całkowity czas podróży: {route.total_time:.1f} min",
        f"🔄 Liczba przesiadek: {max(0, route.transfers)}",
    ]
    
    table = PrettyTable()
    table.field_names = ["Linia", "Skąd", "Dokąd", "Odjazd", "Przyjazd"]
    table.align["Linia"] = "l"
    table.align["Skąd"] = "l"
    table.align["Dokąd"] = "l"
    table.align["Odjazd"] = "l"
    table.align["Przyjazd"] = "l"
    
    segments = route.get_segments()
    
    for segment in segments:
        if segment['line'] == 'wait':
            continue
        
        line = segment['line']
        start_stop = segment['start_stop']
        end_stop = segment['end_stop']
        departure = segment['departure_time']
        arrival = segment['arrival_time']
        
        table.add_row([
            line, 
            start_stop, 
            end_stop, 
            minutes_to_time(departure), 
            minutes_to_time(arrival)
        ])
    
    result = "🚉 SZCZEGÓŁY TRASY:\n"
    result += "\n".join(summary)
    result += "\n\n" + str(table)
    
    return result