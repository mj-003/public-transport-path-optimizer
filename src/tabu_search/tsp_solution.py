class TSPSolution:
    """Reprezentuje rozwiązanie problemu komiwojażera (TSP) jako permutację przystanków"""
    def __init__(self, stops_sequence, total_time=None, total_transfers=None, routes=None):
        self.stops_sequence = stops_sequence  # Sekwencja przystanków do odwiedzenia
        self.total_time = total_time or 0  # Całkowity czas podróży
        self.total_transfers = total_transfers or 0  # Całkowita liczba przesiadek
        self.routes = routes or []  # Lista tras między kolejnymi przystankami
    
    def clone(self):
        """Tworzy kopię rozwiązania"""
        return TSPSolution(
            self.stops_sequence.copy(),
            self.total_time,
            self.total_transfers,
            self.routes.copy()
        )
    
    def __repr__(self):
        return f"TSPSolution({' -> '.join(self.stops_sequence)}, time: {self.total_time:.1f} min, transfers: {self.total_transfers})"
