from collections import deque
import random
from .tsp_solution import TSPSolution
from src.data_structures import TransportRoute, TransportConnection, TransportStop
from src.algorithms.dijkstra import dijkstra_shortest_path
from src.utils import minutes_to_time
from tqdm import tqdm

class TabuSearchTSP:
    """Implementacja algorytmu Tabu Search dla problemu TSP w sieci komunikacji miejskiej"""
    def __init__(self, stops, criterion='time', transfer_time=3, tabu_size=None, use_aspiration=False):
        self.stops = stops
        self.criterion = criterion  
        self.transfer_time = transfer_time
        self.tabu_list = deque(maxlen=tabu_size)  
        self.use_aspiration = use_aspiration
        
        self.objective_functions = {
            'time': self._evaluate_time,
            'transfers': self._evaluate_transfers
        }
        
        self.aspiration_history = {}  
        self.aspiration_decay = 0.9  
    
    def generate_initial_solution(self, start_stop, stops_to_visit, start_time):
        """Generuje początkowe rozwiązanie (kolejność odwiedzania przystanków)"""
        stops_sequence = [start_stop] + stops_to_visit + [start_stop]
        solution = TSPSolution(stops_sequence)
        self._evaluate_solution(solution, start_time)
        
        return solution
    
    def _evaluate_solution(self, solution, start_time):
        """Ocenia jakość rozwiązania obliczając czas podróży i liczbę przesiadek"""
        total_time = 0
        total_transfers = 0
        routes = []
        
        current_time = start_time
        
        for i in range(len(solution.stops_sequence) - 1):
            from_stop = solution.stops_sequence[i]
            to_stop = solution.stops_sequence[i+1]
            
            current_time_str = minutes_to_time(int(current_time))
            route = dijkstra_shortest_path(
                self.stops, 
                from_stop, 
                to_stop, 
                current_time_str,
                self.transfer_time
            )
            
            if not route.connections:
                solution.total_time = float('inf')
                solution.total_transfers = float('inf')
                solution.routes = []
                return
            
            route.calculate_stats()
            total_time += route.total_time + route.waiting_time
            total_transfers += route.transfers
            routes.append(route)
            
            if route.connections:
                current_time = route.connections[-1].arrival_time
        
        solution.total_time = total_time
        solution.total_transfers = total_transfers
        solution.routes = routes
    
    def _evaluate_time(self, solution):
        """Funkcja celu dla kryterium czasu"""
        return solution.total_time
    
    def _evaluate_transfers(self, solution):
        """Funkcja celu dla kryterium liczby przesiadek"""
        return solution.total_transfers * 100 + solution.total_time
    
    def generate_neighbors(self, solution, sample_size=None):
        """Generuje sąsiedztwo rozwiązania poprzez zamianę kolejności przystanków"""
        neighbors = []
        
        stops_to_permute = solution.stops_sequence[1:-1]
                
        swap_pairs = []
        for i in range(len(stops_to_permute)):
            for j in range(i+1, len(stops_to_permute)):
                swap_pairs.append((i+1, j+1))  # +1 bo pomijamy pierwszy przystanek
        
        if sample_size and len(swap_pairs) > sample_size:
            swap_pairs = random.sample(swap_pairs, sample_size)
        
        for i, j in swap_pairs:
            neighbor = solution.clone()
            
            neighbor.stops_sequence[i], neighbor.stops_sequence[j] = neighbor.stops_sequence[j], neighbor.stops_sequence[i]
            
            neighbors.append((neighbor, (i, j)))
        
        return neighbors
    
    def update_aspiration_history(self, move):
        """Aktualizuje historię ruchów dla mechanizmu aspiracji"""
        for key in self.aspiration_history:
            self.aspiration_history[key] *= self.aspiration_decay
        
        if move in self.aspiration_history:
            self.aspiration_history[move] += 1
        else:
            self.aspiration_history[move] = 1
    
    def _is_move_in_tabu_list(self, move):
        """Sprawdza, czy ruch jest na liście tabu"""
        return move in self.tabu_list
    
    def _aspiration_criterion(self, new_cost, best_cost, move):
        """Sprawdza, czy ruch spełnia kryterium aspiracji"""
        if not self.use_aspiration:
            return False
        
        if new_cost < best_cost:
            return True
        
        move_freq = self.aspiration_history.get(move, 0)
        if move_freq < 0.5:  
            return True
        
        return False
    
    def run(self, start_stop, stops_to_visit, start_time, max_iterations=100, sample_size=None):
        """Uruchamia algorytm Tabu Search dla problemu TSP"""
        current_solution = self.generate_initial_solution(start_stop, stops_to_visit, start_time)
        
        best_solution = current_solution.clone()
        best_cost = self.objective_functions[self.criterion](best_solution)
        
        if self.tabu_list.maxlen is None:
            self.tabu_list = deque(maxlen=len(stops_to_visit) // 2 + 1)
        
        for iteration in tqdm(range(max_iterations), desc="Tabu Search Progress"):
            neighbors = self.generate_neighbors(current_solution, sample_size)
            
            best_neighbor = None
            best_neighbor_cost = float('inf')
            best_move = None
            
            for neighbor, move in neighbors:
                self._evaluate_solution(neighbor, start_time)
                neighbor_cost = self.objective_functions[self.criterion](neighbor)
                
                is_tabu = self._is_move_in_tabu_list(move) or self._is_move_in_tabu_list((move[1], move[0]))
                
                aspiration = self._aspiration_criterion(neighbor_cost, best_cost, move)
                
                if (not is_tabu or aspiration) and neighbor_cost < best_neighbor_cost:
                    best_neighbor = neighbor
                    best_neighbor_cost = neighbor_cost
                    best_move = move
            
            if best_neighbor is None:
                break
            
            current_solution = best_neighbor
            
            if best_neighbor_cost < best_cost:
                best_solution = best_neighbor.clone()
                best_cost = best_neighbor_cost
            
            self.tabu_list.append(best_move)
            
            if self.use_aspiration:
                self.update_aspiration_history(best_move)
        
        return best_solution
    
    def combine_routes(self, solution):
        """Łączy poszczególne trasy w jedną trasę całkowitą"""
        combined_route = TransportRoute()
        
        for route in solution.routes:
            for conn in route.connections:
                combined_route.add_connection(conn)
        
        combined_route.calculate_stats()
        
        return combined_route

def determine_tabu_size(num_stops):
    """Określa optymalny rozmiar listy tabu w zależności od liczby przystanków"""
    if num_stops <= 5:
        return max(3, num_stops // 2)
    elif num_stops <= 15:
        return max(5, num_stops // 2)
    else:
        return max(7, num_stops // 2)