#!/usr/bin/env python3
"""
Pathfinder Race - Algorithm Visualization
==========================================
Watch different pathfinding algorithms compete in real-time:
- A* (A-Star): Optimal with heuristic guidance
- Dijkstra: Guaranteed shortest path
- BFS: Breadth-first exploration
- Greedy Best-First: Fast but suboptimal

Features procedural maze generation and step-by-step visualization.

Author: Claude (Opus 4.5)
"""

import heapq
import random
import time
import sys
import os
from dataclasses import dataclass, field
from typing import List, Set, Dict, Tuple, Optional
from enum import Enum
from collections import deque

# Terminal colors
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Cell types
    WALL = '\033[48;5;236m'  # Dark gray background
    PATH = '\033[48;5;255m'  # White background
    START = '\033[48;5;46m'  # Bright green
    END = '\033[48;5;196m'   # Bright red

    # Algorithm colors (for visited/exploring)
    ASTAR = '\033[48;5;39m'      # Blue
    DIJKSTRA = '\033[48;5;208m'  # Orange
    BFS = '\033[48;5;164m'       # Purple
    GREEDY = '\033[48;5;226m'    # Yellow

    # Final path colors
    ASTAR_PATH = '\033[48;5;27m'
    DIJKSTRA_PATH = '\033[48;5;202m'
    BFS_PATH = '\033[48;5;128m'
    GREEDY_PATH = '\033[48;5;220m'

    # Text colors for overlay
    TEXT_DARK = '\033[38;5;232m'
    TEXT_LIGHT = '\033[38;5;255m'


class CellType(Enum):
    EMPTY = 0
    WALL = 1
    START = 2
    END = 3


@dataclass(order=True)
class PriorityNode:
    """Node for priority queue with comparison support."""
    priority: float
    position: Tuple[int, int] = field(compare=False)


class Maze:
    """
    Procedural maze generator using recursive backtracking.
    """

    def __init__(self, width: int, height: int):
        # Ensure odd dimensions for proper maze
        self.width = width if width % 2 == 1 else width - 1
        self.height = height if height % 2 == 1 else height - 1
        self.grid: List[List[CellType]] = []
        self.start = (1, 1)
        self.end = (self.width - 2, self.height - 2)

    def generate(self):
        """Generate maze using recursive backtracking."""
        # Fill with walls
        self.grid = [[CellType.WALL for _ in range(self.width)]
                     for _ in range(self.height)]

        # Carve passages
        self._carve(1, 1)

        # Set start and end
        self.grid[self.start[1]][self.start[0]] = CellType.START
        self.grid[self.end[1]][self.end[0]] = CellType.END

        # Ensure path exists by carving if needed
        self._ensure_solvable()

    def _carve(self, x: int, y: int):
        """Recursive backtracking maze carving."""
        self.grid[y][x] = CellType.EMPTY

        directions = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        random.shuffle(directions)

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if (0 < nx < self.width - 1 and 0 < ny < self.height - 1
                    and self.grid[ny][nx] == CellType.WALL):
                # Carve wall between current and next cell
                self.grid[y + dy // 2][x + dx // 2] = CellType.EMPTY
                self._carve(nx, ny)

    def _ensure_solvable(self):
        """Make sure there's a path from start to end."""
        # Simple BFS to check connectivity
        visited = set()
        queue = deque([self.start])
        visited.add(self.start)

        while queue:
            x, y = queue.popleft()
            if (x, y) == self.end:
                return  # Already solvable

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < self.width and 0 <= ny < self.height
                        and (nx, ny) not in visited
                        and self.grid[ny][nx] != CellType.WALL):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        # Not solvable - carve a direct path
        x, y = self.start
        while (x, y) != self.end:
            if x < self.end[0]:
                x += 1
            elif y < self.end[1]:
                y += 1
            if self.grid[y][x] == CellType.WALL:
                self.grid[y][x] = CellType.EMPTY

    def get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get valid neighboring positions."""
        x, y = pos
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < self.width and 0 <= ny < self.height
                    and self.grid[ny][nx] != CellType.WALL):
                neighbors.append((nx, ny))
        return neighbors

    def is_valid(self, pos: Tuple[int, int]) -> bool:
        """Check if position is valid and not a wall."""
        x, y = pos
        return (0 <= x < self.width and 0 <= y < self.height
                and self.grid[y][x] != CellType.WALL)


class PathfindingAlgorithm:
    """Base class for pathfinding algorithms."""

    def __init__(self, name: str, color: str, path_color: str):
        self.name = name
        self.color = color
        self.path_color = path_color
        self.visited: Set[Tuple[int, int]] = set()
        self.came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self.current: Optional[Tuple[int, int]] = None
        self.path: List[Tuple[int, int]] = []
        self.finished = False
        self.found_path = False
        self.steps = 0

    def reset(self, start: Tuple[int, int]):
        """Reset algorithm state."""
        self.visited = {start}
        self.came_from = {}
        self.current = start
        self.path = []
        self.finished = False
        self.found_path = False
        self.steps = 0

    def step(self, maze: Maze) -> bool:
        """Perform one step of the algorithm. Returns True if done."""
        raise NotImplementedError

    def reconstruct_path(self, end: Tuple[int, int]):
        """Reconstruct path from start to end."""
        self.path = []
        current = end
        while current in self.came_from:
            self.path.append(current)
            current = self.came_from[current]
        self.path.append(current)
        self.path.reverse()


class AStarAlgorithm(PathfindingAlgorithm):
    """A* pathfinding with Manhattan distance heuristic."""

    def __init__(self):
        super().__init__("A*", Colors.ASTAR, Colors.ASTAR_PATH)
        self.open_set: List[PriorityNode] = []
        self.g_score: Dict[Tuple[int, int], float] = {}
        self.f_score: Dict[Tuple[int, int], float] = {}

    def reset(self, start: Tuple[int, int]):
        super().reset(start)
        self.open_set = [PriorityNode(0, start)]
        self.g_score = {start: 0}
        self.f_score = {start: 0}

    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Manhattan distance heuristic."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def step(self, maze: Maze) -> bool:
        if not self.open_set or self.finished:
            self.finished = True
            return True

        self.steps += 1

        # Get lowest f_score node
        node = heapq.heappop(self.open_set)
        self.current = node.position

        if self.current == maze.end:
            self.finished = True
            self.found_path = True
            self.reconstruct_path(maze.end)
            return True

        for neighbor in maze.get_neighbors(self.current):
            tentative_g = self.g_score.get(self.current, float('inf')) + 1

            if tentative_g < self.g_score.get(neighbor, float('inf')):
                self.came_from[neighbor] = self.current
                self.g_score[neighbor] = tentative_g
                f = tentative_g + self._heuristic(neighbor, maze.end)
                self.f_score[neighbor] = f

                if neighbor not in self.visited:
                    self.visited.add(neighbor)
                    heapq.heappush(self.open_set, PriorityNode(f, neighbor))

        return False


class DijkstraAlgorithm(PathfindingAlgorithm):
    """Dijkstra's algorithm - guaranteed shortest path."""

    def __init__(self):
        super().__init__("Dijkstra", Colors.DIJKSTRA, Colors.DIJKSTRA_PATH)
        self.open_set: List[PriorityNode] = []
        self.distances: Dict[Tuple[int, int], float] = {}

    def reset(self, start: Tuple[int, int]):
        super().reset(start)
        self.open_set = [PriorityNode(0, start)]
        self.distances = {start: 0}

    def step(self, maze: Maze) -> bool:
        if not self.open_set or self.finished:
            self.finished = True
            return True

        self.steps += 1

        node = heapq.heappop(self.open_set)
        self.current = node.position

        if self.current == maze.end:
            self.finished = True
            self.found_path = True
            self.reconstruct_path(maze.end)
            return True

        for neighbor in maze.get_neighbors(self.current):
            new_dist = self.distances.get(self.current, float('inf')) + 1

            if new_dist < self.distances.get(neighbor, float('inf')):
                self.distances[neighbor] = new_dist
                self.came_from[neighbor] = self.current

                if neighbor not in self.visited:
                    self.visited.add(neighbor)
                    heapq.heappush(self.open_set, PriorityNode(new_dist, neighbor))

        return False


class BFSAlgorithm(PathfindingAlgorithm):
    """Breadth-First Search - explores in layers."""

    def __init__(self):
        super().__init__("BFS", Colors.BFS, Colors.BFS_PATH)
        self.queue: deque = deque()

    def reset(self, start: Tuple[int, int]):
        super().reset(start)
        self.queue = deque([start])

    def step(self, maze: Maze) -> bool:
        if not self.queue or self.finished:
            self.finished = True
            return True

        self.steps += 1
        self.current = self.queue.popleft()

        if self.current == maze.end:
            self.finished = True
            self.found_path = True
            self.reconstruct_path(maze.end)
            return True

        for neighbor in maze.get_neighbors(self.current):
            if neighbor not in self.visited:
                self.visited.add(neighbor)
                self.came_from[neighbor] = self.current
                self.queue.append(neighbor)

        return False


class GreedyBestFirstAlgorithm(PathfindingAlgorithm):
    """Greedy Best-First - follows heuristic only."""

    def __init__(self):
        super().__init__("Greedy", Colors.GREEDY, Colors.GREEDY_PATH)
        self.open_set: List[PriorityNode] = []

    def reset(self, start: Tuple[int, int]):
        super().reset(start)
        self.open_set = [PriorityNode(0, start)]

    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def step(self, maze: Maze) -> bool:
        if not self.open_set or self.finished:
            self.finished = True
            return True

        self.steps += 1

        node = heapq.heappop(self.open_set)
        self.current = node.position

        if self.current == maze.end:
            self.finished = True
            self.found_path = True
            self.reconstruct_path(maze.end)
            return True

        for neighbor in maze.get_neighbors(self.current):
            if neighbor not in self.visited:
                self.visited.add(neighbor)
                self.came_from[neighbor] = self.current
                h = self._heuristic(neighbor, maze.end)
                heapq.heappush(self.open_set, PriorityNode(h, neighbor))

        return False


class PathfinderRace:
    """
    Main visualization engine that runs multiple algorithms simultaneously.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.maze = Maze(width, height)
        self.algorithms: List[PathfindingAlgorithm] = [
            AStarAlgorithm(),
            DijkstraAlgorithm(),
            BFSAlgorithm(),
            GreedyBestFirstAlgorithm()
        ]

    def new_maze(self):
        """Generate a new maze and reset all algorithms."""
        self.maze.generate()
        for algo in self.algorithms:
            algo.reset(self.maze.start)

    def step_all(self) -> bool:
        """Step all algorithms. Returns True when all are done."""
        all_done = True
        for algo in self.algorithms:
            if not algo.finished:
                algo.step(self.maze)
                if not algo.finished:
                    all_done = False
        return all_done

    def render(self) -> str:
        """Render the maze with all algorithm states overlaid."""
        # Initialize render buffer
        buffer = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        bg_colors = [['' for _ in range(self.width)] for _ in range(self.height)]

        # Draw base maze
        for y in range(self.height):
            for x in range(self.width):
                cell = self.maze.grid[y][x]
                if cell == CellType.WALL:
                    buffer[y][x] = '█'
                    bg_colors[y][x] = Colors.WALL
                elif cell == CellType.START:
                    buffer[y][x] = 'S'
                    bg_colors[y][x] = Colors.START
                elif cell == CellType.END:
                    buffer[y][x] = 'E'
                    bg_colors[y][x] = Colors.END
                else:
                    buffer[y][x] = ' '

        # Overlay algorithm visited cells (with mixing for overlaps)
        visited_counts: Dict[Tuple[int, int], List[str]] = {}
        for algo in self.algorithms:
            for pos in algo.visited:
                if pos not in visited_counts:
                    visited_counts[pos] = []
                visited_counts[pos].append(algo.color)

        for (x, y), colors in visited_counts.items():
            if self.maze.grid[y][x] in (CellType.EMPTY,):
                # Use first algorithm's color or show mixed
                bg_colors[y][x] = colors[0]
                if len(colors) > 1:
                    buffer[y][x] = '·'
                else:
                    buffer[y][x] = '░'

        # Overlay final paths (finished algorithms)
        for algo in self.algorithms:
            if algo.found_path:
                for pos in algo.path:
                    x, y = pos
                    if self.maze.grid[y][x] == CellType.EMPTY:
                        bg_colors[y][x] = algo.path_color
                        buffer[y][x] = '█'

        # Mark current positions
        for algo in self.algorithms:
            if algo.current and not algo.finished:
                x, y = algo.current
                if 0 <= x < self.width and 0 <= y < self.height:
                    buffer[y][x] = '●'

        # Build output
        lines = []
        for y in range(self.height):
            line_parts = []
            for x in range(self.width):
                bg = bg_colors[y][x]
                char = buffer[y][x]
                if bg:
                    line_parts.append(f"{bg}{Colors.TEXT_DARK}{char}{Colors.RESET}")
                else:
                    line_parts.append(char)
            lines.append(''.join(line_parts))

        return '\n'.join(lines)

    def get_stats(self) -> str:
        """Get algorithm statistics."""
        stats = []
        for algo in self.algorithms:
            status = "✓" if algo.found_path else ("..." if not algo.finished else "✗")
            path_len = len(algo.path) if algo.path else 0
            stats.append(
                f"{algo.color}  {Colors.RESET} {algo.name:8s}: "
                f"Steps={algo.steps:4d} Path={path_len:3d} {status}"
            )
        return " │ ".join(stats)


def print_header(width: int):
    """Print the race header."""
    print("\033[2J\033[H")  # Clear screen
    title = "⚡ PATHFINDER RACE ⚡"
    subtitle = "A* vs Dijkstra vs BFS vs Greedy Best-First"
    print(f"\033[1;36m{'═' * width}\033[0m")
    print(f"\033[1;33m{title:^{width}}\033[0m")
    print(f"\033[0;37m{subtitle:^{width}}\033[0m")
    print(f"\033[1;36m{'═' * width}\033[0m")


def main():
    """Main race loop."""
    # Get terminal size
    try:
        term_size = os.get_terminal_size()
        # Leave room for stats and borders
        width = min(term_size.columns - 2, 79)
        height = min(term_size.lines - 12, 31)
        # Ensure odd dimensions
        width = width if width % 2 == 1 else width - 1
        height = height if height % 2 == 1 else height - 1
    except OSError:
        width, height = 59, 25

    race = PathfinderRace(width, height)
    print_header(max(width, 60))

    print("\n\033[1;32mLegend:\033[0m", end=" ")
    print(f"{Colors.ASTAR}  {Colors.RESET} A*", end="  ")
    print(f"{Colors.DIJKSTRA}  {Colors.RESET} Dijkstra", end="  ")
    print(f"{Colors.BFS}  {Colors.RESET} BFS", end="  ")
    print(f"{Colors.GREEDY}  {Colors.RESET} Greedy")

    print(f"\033[1;32mGoal:\033[0m {Colors.START} S {Colors.RESET} Start → {Colors.END} E {Colors.RESET} End")
    print("\033[0;90mGenerating maze... Press Ctrl+C to exit\033[0m\n")

    time.sleep(1)

    race_number = 0

    try:
        while True:
            race_number += 1
            race.new_maze()

            print(f"\033[8H")  # Move below header
            print(f"\033[1;35m{'─' * 60}\033[0m")
            print(f"\033[1;33m          RACE #{race_number} - GO!\033[0m")
            print(f"\033[1;35m{'─' * 60}\033[0m\n")

            frame_count = 0
            while True:
                frame_start = time.time()

                # Step algorithms
                all_done = race.step_all()

                # Render
                frame = race.render()
                sys.stdout.write("\033[12H")  # Position below race header
                print(frame)
                print()
                print(race.get_stats())
                sys.stdout.flush()

                frame_count += 1

                if all_done:
                    # Show final results
                    print(f"\n\033[1;32m{'─' * 60}\033[0m")

                    # Determine winner
                    finished = [(a.steps, a.name, len(a.path))
                                for a in race.algorithms if a.found_path]
                    if finished:
                        finished.sort()
                        winner = finished[0]
                        print(f"\033[1;33m  🏆 Winner: {winner[1]} "
                              f"(Steps: {winner[0]}, Path: {winner[2]})\033[0m")

                    print(f"\033[1;32m{'─' * 60}\033[0m")
                    print("\033[0;90mStarting next race in 3 seconds...\033[0m")
                    time.sleep(3)
                    break

                # Control speed - faster at first, slower as we progress
                elapsed = time.time() - frame_start
                delay = 0.02 if frame_count < 50 else 0.01
                sleep_time = max(0, delay - elapsed)
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n\n\033[1;36m{'═' * 60}\033[0m")
        print(f"\033[1;33m  Thanks for watching {race_number} races!\033[0m")
        print(f"\033[1;36m{'═' * 60}\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
