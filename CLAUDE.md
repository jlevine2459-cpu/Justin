# CLAUDE.md — AI Assistant Guide for Terminal Graphics Portfolio

## Project Overview

This is a pure-Python educational portfolio demonstrating advanced algorithmic
visualization and graphics techniques rendered entirely in the terminal as ASCII art.
There are no external dependencies, build steps, or databases — every script runs
directly with the Python standard library.

**Author:** Claude (Opus 4.5)
**Language:** Python 3.7+
**Purpose:** Showcase terminal graphics algorithms without GPU dependencies

---

## Repository Structure

```
Justin/
├── README.md               # User-facing documentation
├── CLAUDE.md               # This file
├── raymarcher.py           # 3D ASCII renderer (~459 lines)
├── particle_universe.py    # Physics particle simulation (~455 lines)
└── pathfinder_race.py      # Pathfinding algorithm visualizer (~584 lines)
```

All three scripts are **self-contained and flat** — no packages, modules, or shared
code between them. Each file is fully independent.

---

## Running the Demos

```bash
python3 raymarcher.py         # 3D raymarching engine
python3 particle_universe.py  # Particle physics simulation
python3 pathfinder_race.py    # Algorithm race visualization
```

All demos exit cleanly with **Ctrl+C**. No arguments or environment variables are needed.

**Requirements:**
- Python 3.7+ (standard library only — no pip installs needed)
- Terminal with ANSI color support
- Recommended: 80+ column terminal width

---

## Standard Library Imports Used

The project intentionally avoids all external packages. The only imports used across all scripts:

| Module | Purpose |
|--------|---------|
| `math` | Trigonometry, sqrt, etc. |
| `random` | Noise, procedural generation |
| `time` | Frame timing and sleep |
| `sys` | stdout write and flush |
| `os` | `os.get_terminal_size()` for adaptive layout |
| `dataclasses` | `@dataclass` for structured data types |
| `typing` | Type hints (`List`, `Dict`, `Tuple`, `Set`, `Optional`, `Callable`) |
| `collections` | `defaultdict`, `deque` |
| `heapq` | Priority queue for A*/Dijkstra |
| `enum` | `Enum` for state constants |

**Do not introduce external dependencies.** Adding a `requirements.txt` or any `pip`
package contradicts the design principle of this project.

---

## Key Technical Concepts

### `raymarcher.py`
- **Sphere tracing** through signed distance functions (SDFs)
- **SDF primitives**: spheres, boxes, tori, cylinders, planes
- **Boolean operations**: union, subtraction, intersection, smooth blend
- **Soft shadows** via penumbra estimation
- **Ambient occlusion** with multi-sample approach
- **Recursive reflections** on metallic surfaces
- **Procedural animation**: morphing shapes, orbital camera movement

### `particle_universe.py`
- **Verlet integration** for stable, energy-conserving physics
- **Spatial hashing** for O(n) average-case collision detection
- **Gravitational attraction** toward a moving attractor
- **Velocity-based color coding** (blue → red gradient)
- **Multiple spawn patterns**: explosions, spirals, grids

### `pathfinder_race.py`
- **A\* Search**: optimal pathfinding with Manhattan distance heuristic
- **Dijkstra's Algorithm**: guaranteed shortest path via priority queue
- **BFS**: breadth-first layer-by-layer exploration
- **Greedy Best-First**: heuristic-only, fast but non-optimal
- **Recursive backtracking**: procedural maze generation
- **Simultaneous visualization** of all four algorithms racing

---

## Coding Conventions

These conventions are used consistently across all three scripts:

- **Dataclasses** (`@dataclass`) for structured types (vectors, particles, cells)
- **Type annotations** throughout (`List[Particle]`, `Tuple[int, int]`, etc.)
- **Named constants** in ALL_CAPS at module level for tunable parameters
- **Self-contained rendering loops** using `sys.stdout.write` and `sys.stdout.flush`
  for flicker-free terminal output
- **ANSI escape codes** for colors; terminal cursor positioned with `\033[H`
- **`os.get_terminal_size()`** used with a fallback tuple for adaptive resolution
- **Graceful exit** via `KeyboardInterrupt` catch with cursor/terminal restoration
- **No global mutable state** — simulation state lives in dataclasses or local variables
- **Shebang line**: `#!/usr/bin/env python3` on every script

### ANSI Color Pattern

All scripts use raw ANSI escape codes:

```python
# Foreground color
f"\033[38;2;{r};{g};{b}m{char}\033[0m"

# Cursor home (top-left)
sys.stdout.write("\033[H")

# Clear screen
sys.stdout.write("\033[2J")
```

---

## Development Workflow

### Adding a New Demo

1. Create a new self-contained Python file (e.g., `cellular_automata.py`)
2. Use only standard library imports
3. Follow the existing conventions (dataclasses, type hints, ANSI output, graceful exit)
4. Add a section for it in `README.md`
5. Update `CLAUDE.md` with a description of the key concepts

### Modifying an Existing Demo

- Each script is long but linear — simulation parameters are near the top as constants
- Rendering happens in a `while True` loop using `sys.stdout.write` to a buffer string
- Physics or algorithm state advances once per frame before rendering
- Frame rate is controlled via `time.sleep(...)` at the end of each loop iteration

### Testing

There is no automated test suite. Verification is manual:

```bash
python3 raymarcher.py
python3 particle_universe.py
python3 pathfinder_race.py
```

Confirm each script:
- Starts without error
- Displays animated ASCII art in the terminal
- Exits cleanly with Ctrl+C

---

## Git Workflow

- **Main branch:** `master`
- **Feature branches:** prefixed with `claude/`, e.g. `claude/add-claude-documentation-6TALl`
- **Remote:** `origin` (local proxy at `127.0.0.1:35035`)
- Push with: `git push -u origin <branch-name>`

Commit messages follow an imperative, descriptive style:
```
Add terminal graphics portfolio: 3D raymarcher, particle physics, pathfinding race
```

---

## What NOT to Do

- Do not add external dependencies (`pip install`, `requirements.txt`)
- Do not split scripts into multiple files or packages — keep each demo self-contained
- Do not add a build or compilation step
- Do not add configuration files (`.env`, `config.yaml`, etc.) — all parameters are hardcoded constants
- Do not add CI/CD pipelines unless explicitly requested
- Do not refactor shared utilities into a common module — duplication between scripts is intentional
