# Terminal Graphics Portfolio

Three impressive terminal-based visualizations demonstrating advanced algorithms and graphics techniques—all rendered in ASCII.

## 🌟 The Demos

### 1. `raymarcher.py` - 3D Raymarching Engine
A real-time ASCII 3D renderer using signed distance functions (SDFs).

**Features:**
- **Raymarching**: Sphere-tracing through mathematically defined geometry
- **SDF Primitives**: Spheres, boxes, tori, cylinders, planes
- **Boolean Operations**: Union, subtraction, intersection, smooth blend
- **Soft Shadows**: Penumbra estimation for realistic shadowing
- **Ambient Occlusion**: Multi-sample AO for depth perception
- **Reflections**: Recursive ray bouncing on metallic surfaces
- **Procedural Animation**: Morphing shapes, orbital camera

```bash
python3 raymarcher.py
```

### 2. `particle_universe.py` - Physics Simulation
A particle system with gravitational dynamics and collision detection.

**Features:**
- **Verlet Integration**: Stable, energy-conserving physics
- **Spatial Hashing**: O(n) collision detection via grid partitioning
- **Gravitational Attraction**: Particles orbit a moving attractor
- **Velocity Visualization**: Color-coded by speed (blue→red)
- **Multiple Spawn Patterns**: Explosions, spirals, grids

```bash
python3 particle_universe.py
```

### 3. `pathfinder_race.py` - Algorithm Visualization
Watch four pathfinding algorithms race through procedural mazes.

**Features:**
- **A\* Search**: Optimal pathfinding with Manhattan heuristic
- **Dijkstra's Algorithm**: Guaranteed shortest path
- **BFS**: Layer-by-layer exploration
- **Greedy Best-First**: Heuristic-only speed demon
- **Recursive Backtracking**: Procedural maze generation
- **Live Visualization**: See algorithms explore simultaneously

```bash
python3 pathfinder_race.py
```

## 🛠️ Requirements

- Python 3.7+
- A terminal with ANSI color support
- Recommended: 80+ column terminal width

## 🎮 Controls

All demos: **Ctrl+C** to exit gracefully

## 📐 Technical Highlights

| Demo | Key Technique | Complexity |
|------|--------------|------------|
| Raymarcher | Sphere tracing, SDF composition | O(w×h×steps) |
| Particle Universe | Spatial hash collision detection | O(n) average |
| Pathfinder Race | Priority queue-based search | O(V + E log V) |

---

*Created by Claude (Opus 4.5) - demonstrating that impressive graphics don't need a GPU.*

## ♠ holdem-course.html — Range & Reason

An interactive, self-contained tutoring course for no-limit Texas Hold'em strategy: 8 modules covering EV thinking, positional preflop ranges, pot odds, postflop play, exploitation, and bankroll management — with an interactive range explorer, a pot-odds trainer, per-module quizzes, and a final hand lab. Progress is saved in the browser.

Open `holdem-course.html` in any browser. No dependencies, no network needed.
