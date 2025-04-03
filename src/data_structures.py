from collections import defaultdict
from src.utils import minutes_to_time
from src.utils import time_to_minutes
class TransportConnection:
    """Reprezentuje połączenie transportowe między dwoma przystankami"""
    def __init__(self, line, company, departure_time, arrival_time, 
                 start_stop, end_stop, start_coords=None, end_coords=None):
        self.line = line
        self.company = company
        self.departure_time = departure_time  # w minutach od północy
        self.arrival_time = arrival_time  # w minutach od północy
        self.start_stop = start_stop
        self.end_stop = end_stop
        self.start_coords = start_coords  # (lat, lon)
        self.end_coords = end_coords  # (lat, lon)
        self.travel_time = arrival_time - departure_time
    
    def __repr__(self):
        return f"TransportConnection({self.line}, {minutes_to_time(self.departure_time)} → {minutes_to_time(self.arrival_time)}, {self.start_stop} → {self.end_stop}, {self.travel_time:.1f} min)"
    
    def to_dict(self):
        return {
            'line': self.line,
            'company': self.company,
            'departure_time': minutes_to_time(self.departure_time),
            'arrival_time': minutes_to_time(self.arrival_time),
            'start_stop': self.start_stop,
            'end_stop': self.end_stop,
            'travel_time': self.travel_time
        }

class TransportStop:
    """Reprezentuje przystanek transportowy"""
    def __init__(self, name):
        self.name = name
        self.connections = defaultdict(list)  # end_stop -> [connections]
        self.coordinates = None  # (lat, lon)
    
    def add_connection(self, end_stop, connection):
        """Dodaje połączenie wychodzące z przystanku"""
        self.connections[end_stop].append(connection)
    
    def get_earliest_connection(self, end_stop, current_time, previous_line=None, transfer_time=3):
        """Znajduje najwcześniejsze połączenie do danego przystanku po określonej godzinie"""
        if end_stop not in self.connections:
            return None
        
        earliest_conn = None
        earliest_departure = float('inf')
        
        for conn in self.connections[end_stop]:
            required_time = current_time
            
            if previous_line is not None and conn.line != previous_line and previous_line != 'wait':
                required_time = current_time + transfer_time
            
            
            if conn.departure_time >= required_time and conn.departure_time < earliest_departure:
                earliest_conn = conn
                earliest_departure = conn.departure_time
        
        return earliest_conn
    
    def __repr__(self):
        num_connections = sum(len(conns) for conns in self.connections.values())
        return f"TransportStop({self.name}, {num_connections} connections)"

class TransportRoute:
    """Reprezentuje trasę transportową składającą się z połączeń"""
    def __init__(self, connections=None):
        self.connections = connections or []
        self.total_time = 0
        self.transfers = 0
        self.waiting_time = 0
        
    def add_connection(self, connection):
        self.connections.append(connection)
        

    def calculate_stats(self, start_time=None):
        """Oblicza statystyki trasy"""
        if not self.connections:
            return
            
        self.total_time = 0
        self.transfers = 0
        self.waiting_time = 0
        
        first_departure = self.connections[0].departure_time
        last_arrival = self.connections[-1].arrival_time
        
        if start_time is not None:
            start_time_minutes = time_to_minutes(start_time)
            if start_time_minutes < first_departure:
                self.waiting_time = first_departure - start_time_minutes
                first_departure = start_time_minutes
        
        previous_line = None
        previous_arrival = None
        previous_stop = None
        
        for conn in self.connections:
            if conn.line == 'wait':
                continue
            
            if previous_line is not None and previous_line != conn.line:
                self.transfers += 1
            
            previous_line = conn.line
            previous_arrival = conn.arrival_time
            previous_stop = conn.end_stop
        
        self.total_time = last_arrival - first_departure
        
    def get_segments(self):
        """Zwraca segmenty podróży (odcinki na jednej linii)"""
        segments = []
        current_line = None
        segment_start = None
        segment_conns = []
        
        for conn in self.connections:
            if conn.line == 'wait':
                continue
                
            if current_line is None or current_line != conn.line:
                if current_line is not None:
                    segments.append({
                        'line': current_line,
                        'start_stop': segment_start.start_stop,
                        'end_stop': segment_conns[-1].end_stop,
                        'departure_time': segment_start.departure_time,
                        'arrival_time': segment_conns[-1].arrival_time,
                        'connections': segment_conns
                    })
                
                current_line = conn.line
                segment_start = conn
                segment_conns = [conn]
            else:
                segment_conns.append(conn)
        
        if current_line is not None:
            segments.append({
                'line': current_line,
                'start_stop': segment_start.start_stop,
                'end_stop': segment_conns[-1].end_stop,
                'departure_time': segment_start.departure_time,
                'arrival_time': segment_conns[-1].arrival_time,
                'connections': segment_conns
            })
            
        return segments
    
    def __repr__(self):
        self.calculate_stats()
        return f"TransportRoute({len(self.connections)} connections, {self.total_time:.1f} min, {self.transfers} transfers)"
