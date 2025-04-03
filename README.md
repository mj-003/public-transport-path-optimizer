# Public Transport Path Optimizer
This repository contains an implementation of various path optimization algorithms for the public transport network of Wrocław, Poland. It uses actual public transport schedule data to find optimal routes based on different criteria.

## Features

- Find the shortest path between two stops using:
  - Dijkstra's algorithm (time optimization)
  - A* algorithm (time optimization with heuristics)
  - A* for minimizing transfers
  - Advanced A* with multi-criteria optimization
- Find the optimal route that visits multiple stops using Tabu Search
- Visualize routes on an interactive map
