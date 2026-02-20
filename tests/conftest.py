"""Shared fixtures for terminal graphics portfolio tests."""
import sys
import os
import pytest

# Add project root to path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raymarcher import Vec3, Material, HitInfo, Scene, Raymarcher
from particle_universe import Particle, SpatialHash, ParticleUniverse
from pathfinder_race import (
    Maze, CellType, PriorityNode,
    AStarAlgorithm, DijkstraAlgorithm, BFSAlgorithm,
    GreedyBestFirstAlgorithm, PathfinderRace
)


# ── Raymarcher fixtures ──

@pytest.fixture
def origin():
    return Vec3(0, 0, 0)


@pytest.fixture
def unit_x():
    return Vec3(1, 0, 0)


@pytest.fixture
def unit_y():
    return Vec3(0, 1, 0)


@pytest.fixture
def unit_z():
    return Vec3(0, 0, 1)


@pytest.fixture
def scene():
    return Scene(time=0.0)


@pytest.fixture
def small_renderer():
    return Raymarcher(20, 10)


# ── Particle Universe fixtures ──

@pytest.fixture
def particle_at_origin():
    return Particle(x=0.0, y=0.0)


@pytest.fixture
def spatial_hash():
    return SpatialHash(cell_size=3.0)


@pytest.fixture
def small_universe():
    return ParticleUniverse(width=40, height=20)


# ── Pathfinder fixtures ──

@pytest.fixture
def small_maze():
    """A small maze for fast test execution."""
    m = Maze(11, 11)
    m.generate()
    return m


@pytest.fixture
def race():
    return PathfinderRace(21, 21)
