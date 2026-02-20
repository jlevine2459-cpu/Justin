"""Tests for Maze generation and pathfinding algorithms.

Coverage target: pathfinder_race.py lines 54-481
Priority: HIGH — Pathfinding algorithm correctness is the core value
proposition of this visualization. Maze solvability is a prerequisite.
"""
import math
import random
import pytest
from collections import deque
from pathfinder_race import (
    Maze, CellType, PriorityNode,
    AStarAlgorithm, DijkstraAlgorithm, BFSAlgorithm,
    GreedyBestFirstAlgorithm, PathfinderRace, PathfindingAlgorithm
)


class TestCellType:
    """CellType enum values."""

    def test_cell_types_exist(self):
        assert CellType.EMPTY.value == 0
        assert CellType.WALL.value == 1
        assert CellType.START.value == 2
        assert CellType.END.value == 3


class TestPriorityNode:
    """Priority queue node ordering."""

    def test_ordering_by_priority(self):
        a = PriorityNode(1.0, (0, 0))
        b = PriorityNode(2.0, (1, 1))
        assert a < b

    def test_equal_priority(self):
        a = PriorityNode(1.0, (0, 0))
        b = PriorityNode(1.0, (1, 1))
        assert not (a < b)
        assert not (b < a)


class TestMaze:
    """Maze generation and structural properties."""

    def test_generate_creates_grid(self):
        m = Maze(11, 11)
        m.generate()
        assert len(m.grid) == 11
        assert len(m.grid[0]) == 11

    def test_odd_dimensions_enforced(self):
        m = Maze(10, 12)
        assert m.width == 9
        assert m.height == 11

    def test_already_odd_unchanged(self):
        m = Maze(11, 13)
        assert m.width == 11
        assert m.height == 13

    def test_start_position(self):
        m = Maze(11, 11)
        m.generate()
        assert m.grid[m.start[1]][m.start[0]] == CellType.START

    def test_end_position(self):
        m = Maze(11, 11)
        m.generate()
        assert m.grid[m.end[1]][m.end[0]] == CellType.END

    def test_border_walls(self):
        m = Maze(11, 11)
        m.generate()
        # Top and bottom rows should be all walls (except possibly start/end)
        for x in range(m.width):
            assert m.grid[0][x] == CellType.WALL
            assert m.grid[m.height - 1][x] == CellType.WALL
        # Left and right columns should be all walls
        for y in range(m.height):
            assert m.grid[y][0] == CellType.WALL
            assert m.grid[y][m.width - 1] == CellType.WALL

    def test_maze_is_solvable(self):
        """Every generated maze must have a path from start to end."""
        for _ in range(10):  # Test multiple random mazes
            m = Maze(21, 21)
            m.generate()
            assert _bfs_solvable(m), "Generated maze has no solution!"

    def test_small_maze_solvable(self):
        m = Maze(5, 5)
        m.generate()
        assert _bfs_solvable(m)

    def test_large_maze_solvable(self):
        m = Maze(41, 41)
        m.generate()
        assert _bfs_solvable(m)

    def test_get_neighbors_returns_valid(self):
        m = Maze(11, 11)
        m.generate()
        neighbors = m.get_neighbors(m.start)
        for nx, ny in neighbors:
            assert 0 <= nx < m.width
            assert 0 <= ny < m.height
            assert m.grid[ny][nx] != CellType.WALL

    def test_get_neighbors_excludes_walls(self):
        m = Maze(11, 11)
        m.generate()
        for pos in [(x, y) for y in range(m.height) for x in range(m.width)
                    if m.grid[y][x] != CellType.WALL]:
            neighbors = m.get_neighbors(pos)
            for nx, ny in neighbors:
                assert m.grid[ny][nx] != CellType.WALL

    def test_is_valid_open_cell(self):
        m = Maze(11, 11)
        m.generate()
        assert m.is_valid(m.start)
        assert m.is_valid(m.end)

    def test_is_valid_wall_cell(self):
        m = Maze(11, 11)
        m.generate()
        # (0, 0) is always a wall
        assert not m.is_valid((0, 0))

    def test_is_valid_out_of_bounds(self):
        m = Maze(11, 11)
        m.generate()
        assert not m.is_valid((-1, 0))
        assert not m.is_valid((0, -1))
        assert not m.is_valid((11, 0))
        assert not m.is_valid((0, 11))


class TestPathfindingBase:
    """Base PathfindingAlgorithm class behavior."""

    def test_reset_clears_state(self):
        algo = AStarAlgorithm()
        algo.reset((1, 1))
        assert algo.current == (1, 1)
        assert (1, 1) in algo.visited
        assert algo.finished is False
        assert algo.found_path is False
        assert algo.steps == 0
        assert algo.path == []

    def test_reconstruct_path(self):
        algo = AStarAlgorithm()
        algo.came_from = {
            (3, 3): (2, 3),
            (2, 3): (1, 3),
            (1, 3): (1, 2),
            (1, 2): (1, 1),
        }
        algo.reconstruct_path((3, 3))
        assert algo.path[0] == (1, 1)
        assert algo.path[-1] == (3, 3)
        assert len(algo.path) == 5


class TestAStarAlgorithm:
    """A* pathfinding with Manhattan distance heuristic."""

    def test_finds_path(self):
        m = Maze(11, 11)
        m.generate()
        algo = AStarAlgorithm()
        algo.reset(m.start)
        _run_until_done(algo, m)
        assert algo.found_path
        assert len(algo.path) > 0
        assert algo.path[0] == m.start
        assert algo.path[-1] == m.end

    def test_heuristic_zero_at_target(self):
        algo = AStarAlgorithm()
        assert algo._heuristic((5, 5), (5, 5)) == 0

    def test_heuristic_manhattan(self):
        algo = AStarAlgorithm()
        assert algo._heuristic((0, 0), (3, 4)) == 7

    def test_heuristic_symmetric(self):
        algo = AStarAlgorithm()
        assert algo._heuristic((0, 0), (3, 4)) == algo._heuristic((3, 4), (0, 0))

    def test_visits_cells(self):
        m = Maze(11, 11)
        m.generate()
        algo = AStarAlgorithm()
        algo.reset(m.start)
        _run_until_done(algo, m)
        assert len(algo.visited) > 1

    def test_step_increments_count(self):
        m = Maze(11, 11)
        m.generate()
        algo = AStarAlgorithm()
        algo.reset(m.start)
        algo.step(m)
        assert algo.steps == 1


class TestDijkstraAlgorithm:
    """Dijkstra's shortest path algorithm."""

    def test_finds_path(self):
        m = Maze(11, 11)
        m.generate()
        algo = DijkstraAlgorithm()
        algo.reset(m.start)
        _run_until_done(algo, m)
        assert algo.found_path
        assert algo.path[0] == m.start
        assert algo.path[-1] == m.end

    def test_path_is_shortest(self):
        """Dijkstra should find the same length path as BFS (uniform cost)."""
        m = Maze(11, 11)
        m.generate()

        dijkstra = DijkstraAlgorithm()
        dijkstra.reset(m.start)
        _run_until_done(dijkstra, m)

        bfs = BFSAlgorithm()
        bfs.reset(m.start)
        _run_until_done(bfs, m)

        # On unweighted graphs, Dijkstra and BFS should find same-length paths
        assert len(dijkstra.path) == len(bfs.path)


class TestBFSAlgorithm:
    """Breadth-first search algorithm."""

    def test_finds_path(self):
        m = Maze(11, 11)
        m.generate()
        algo = BFSAlgorithm()
        algo.reset(m.start)
        _run_until_done(algo, m)
        assert algo.found_path
        assert algo.path[0] == m.start
        assert algo.path[-1] == m.end

    def test_path_is_valid(self):
        """Every consecutive pair in the path should be adjacent."""
        m = Maze(11, 11)
        m.generate()
        algo = BFSAlgorithm()
        algo.reset(m.start)
        _run_until_done(algo, m)
        for i in range(len(algo.path) - 1):
            x1, y1 = algo.path[i]
            x2, y2 = algo.path[i + 1]
            assert abs(x1 - x2) + abs(y1 - y2) == 1, \
                f"Non-adjacent path cells: {algo.path[i]} -> {algo.path[i+1]}"

    def test_path_avoids_walls(self):
        m = Maze(11, 11)
        m.generate()
        algo = BFSAlgorithm()
        algo.reset(m.start)
        _run_until_done(algo, m)
        for x, y in algo.path:
            assert m.grid[y][x] != CellType.WALL


class TestGreedyBestFirstAlgorithm:
    """Greedy best-first search algorithm."""

    def test_finds_path(self):
        m = Maze(11, 11)
        m.generate()
        algo = GreedyBestFirstAlgorithm()
        algo.reset(m.start)
        _run_until_done(algo, m)
        assert algo.found_path

    def test_heuristic_manhattan(self):
        algo = GreedyBestFirstAlgorithm()
        assert algo._heuristic((0, 0), (3, 4)) == 7

    def test_path_is_valid_sequence(self):
        m = Maze(11, 11)
        m.generate()
        algo = GreedyBestFirstAlgorithm()
        algo.reset(m.start)
        _run_until_done(algo, m)
        if algo.found_path:
            for i in range(len(algo.path) - 1):
                x1, y1 = algo.path[i]
                x2, y2 = algo.path[i + 1]
                assert abs(x1 - x2) + abs(y1 - y2) == 1


class TestAlgorithmComparison:
    """Cross-algorithm behavioral comparisons."""

    def test_all_algorithms_find_path(self):
        m = Maze(21, 21)
        m.generate()
        for AlgoClass in [AStarAlgorithm, DijkstraAlgorithm,
                          BFSAlgorithm, GreedyBestFirstAlgorithm]:
            algo = AlgoClass()
            algo.reset(m.start)
            _run_until_done(algo, m)
            assert algo.found_path, f"{algo.name} failed to find a path"

    def test_astar_optimal(self):
        """A* should find a path no longer than BFS (both optimal on unit graphs)."""
        m = Maze(21, 21)
        m.generate()

        astar = AStarAlgorithm()
        astar.reset(m.start)
        _run_until_done(astar, m)

        bfs = BFSAlgorithm()
        bfs.reset(m.start)
        _run_until_done(bfs, m)

        assert len(astar.path) == len(bfs.path)

    def test_astar_fewer_steps_than_dijkstra(self):
        """A* should generally visit fewer cells than Dijkstra due to heuristic."""
        fewer_count = 0
        for _ in range(10):
            m = Maze(21, 21)
            m.generate()

            astar = AStarAlgorithm()
            astar.reset(m.start)
            _run_until_done(astar, m)

            dijkstra = DijkstraAlgorithm()
            dijkstra.reset(m.start)
            _run_until_done(dijkstra, m)

            if len(astar.visited) <= len(dijkstra.visited):
                fewer_count += 1

        # A* should visit fewer (or equal) cells in most cases
        assert fewer_count >= 7, \
            f"A* only visited fewer cells than Dijkstra in {fewer_count}/10 trials"


class TestPathfinderRace:
    """Integration tests for the race engine."""

    def test_new_maze_resets_algorithms(self):
        race = PathfinderRace(21, 21)
        race.new_maze()
        for algo in race.algorithms:
            assert algo.finished is False
            assert algo.steps == 0
            assert algo.current == race.maze.start

    def test_step_all_progresses(self):
        race = PathfinderRace(21, 21)
        race.new_maze()
        race.step_all()
        total_steps = sum(a.steps for a in race.algorithms)
        assert total_steps > 0

    def test_step_all_completes(self):
        race = PathfinderRace(21, 21)
        race.new_maze()
        for _ in range(10000):
            if race.step_all():
                break
        assert all(a.finished for a in race.algorithms)

    def test_render_produces_output(self):
        race = PathfinderRace(21, 21)
        race.new_maze()
        output = race.render()
        assert isinstance(output, str)
        assert len(output) > 0

    def test_get_stats_format(self):
        race = PathfinderRace(21, 21)
        race.new_maze()
        stats = race.get_stats()
        assert "A*" in stats
        assert "Dijkstra" in stats
        assert "BFS" in stats
        assert "Greedy" in stats

    def test_four_algorithms_registered(self):
        race = PathfinderRace(21, 21)
        assert len(race.algorithms) == 4


# ── Helper functions ──

def _bfs_solvable(maze: Maze) -> bool:
    """Check if a maze is solvable using BFS."""
    visited = set()
    queue = deque([maze.start])
    visited.add(maze.start)
    while queue:
        x, y = queue.popleft()
        if (x, y) == maze.end:
            return True
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < maze.width and 0 <= ny < maze.height
                    and (nx, ny) not in visited
                    and maze.grid[ny][nx] != CellType.WALL):
                visited.add((nx, ny))
                queue.append((nx, ny))
    return False


def _run_until_done(algo, maze: Maze, max_iterations: int = 10000):
    """Run a pathfinding algorithm to completion."""
    for _ in range(max_iterations):
        if algo.step(maze):
            break
