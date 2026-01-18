#!/usr/bin/env python3
"""
Particle Universe - Terminal Physics Simulation
================================================
An interactive particle system featuring:
- Verlet integration for stable physics
- Spatial hashing for O(n) collision detection
- Gravitational attraction between particles
- Boundary collisions with energy conservation
- Real-time color-coded velocity visualization

Author: Claude (Opus 4.5)
"""

import math
import random
import time
import sys
import os
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set
from collections import defaultdict

# ANSI color codes for velocity-based coloring
COLORS = [
    '\033[38;5;21m',   # Blue (slow)
    '\033[38;5;27m',
    '\033[38;5;33m',
    '\033[38;5;39m',
    '\033[38;5;45m',   # Cyan
    '\033[38;5;51m',
    '\033[38;5;48m',
    '\033[38;5;46m',   # Green
    '\033[38;5;82m',
    '\033[38;5;118m',
    '\033[38;5;154m',  # Yellow-green
    '\033[38;5;190m',
    '\033[38;5;226m',  # Yellow
    '\033[38;5;220m',
    '\033[38;5;214m',  # Orange
    '\033[38;5;208m',
    '\033[38;5;202m',
    '\033[38;5;196m',  # Red (fast)
]
RESET = '\033[0m'

# Particle characters by size
PARTICLE_CHARS = ['·', '•', '●', '◉', '⬤']


@dataclass
class Particle:
    """
    A particle with position, velocity, and physical properties.
    Uses Verlet integration for stability.
    """
    x: float
    y: float
    prev_x: float = None
    prev_y: float = None
    mass: float = 1.0
    radius: float = 0.5
    fixed: bool = False

    def __post_init__(self):
        if self.prev_x is None:
            self.prev_x = self.x
        if self.prev_y is None:
            self.prev_y = self.y

    @property
    def vx(self) -> float:
        return self.x - self.prev_x

    @property
    def vy(self) -> float:
        return self.y - self.prev_y

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2)

    def apply_force(self, fx: float, fy: float, dt: float = 1.0):
        """Apply force as acceleration (F = ma, a = F/m)."""
        ax = fx / self.mass
        ay = fy / self.mass
        self.x += ax * dt * dt
        self.y += ay * dt * dt


class SpatialHash:
    """
    Spatial hashing for efficient collision detection.
    Divides space into a grid for O(1) neighbor lookups.
    """

    def __init__(self, cell_size: float):
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int], List[Particle]] = defaultdict(list)

    def clear(self):
        self.grid.clear()

    def _hash(self, x: float, y: float) -> Tuple[int, int]:
        return (int(x / self.cell_size), int(y / self.cell_size))

    def insert(self, particle: Particle):
        cell = self._hash(particle.x, particle.y)
        self.grid[cell].append(particle)

    def get_nearby(self, particle: Particle) -> List[Particle]:
        """Get all particles in adjacent cells."""
        cx, cy = self._hash(particle.x, particle.y)
        nearby = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nearby.extend(self.grid.get((cx + dx, cy + dy), []))
        return nearby


class ParticleUniverse:
    """
    The main physics simulation engine.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.particles: List[Particle] = []

        # Physics parameters
        self.gravity = 0.1
        self.damping = 0.998
        self.collision_damping = 0.85
        self.attraction_strength = 0.0002
        self.repulsion_strength = 0.5

        # Spatial partitioning
        self.spatial_hash = SpatialHash(cell_size=3.0)

        # Simulation state
        self.attractor_x = width / 2
        self.attractor_y = height / 2
        self.attractor_active = True
        self.time = 0.0

    def add_particle(self, x: float, y: float, vx: float = 0, vy: float = 0,
                     mass: float = 1.0, radius: float = 0.5):
        """Add a particle with initial velocity."""
        p = Particle(x=x, y=y, mass=mass, radius=radius)
        p.prev_x = x - vx
        p.prev_y = y - vy
        self.particles.append(p)

    def spawn_explosion(self, x: float, y: float, count: int = 30):
        """Create an explosion of particles."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2.0)
            mass = random.uniform(0.5, 2.0)
            self.add_particle(
                x, y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                mass=mass,
                radius=0.3 + mass * 0.2
            )

    def spawn_spiral(self, cx: float, cy: float, count: int = 50):
        """Create a spiral pattern of particles."""
        for i in range(count):
            t = i / count * 4 * math.pi
            r = 2 + t * 2
            x = cx + r * math.cos(t)
            y = cy + r * math.sin(t)
            # Tangential velocity for orbital motion
            vx = -math.sin(t) * 0.5
            vy = math.cos(t) * 0.5
            self.add_particle(x, y, vx, vy, mass=1.0)

    def spawn_grid(self, x1: float, y1: float, x2: float, y2: float,
                   spacing: float = 2.0):
        """Create a grid of particles."""
        x = x1
        while x <= x2:
            y = y1
            while y <= y2:
                self.add_particle(x, y, 0, 0, mass=random.uniform(0.8, 1.2))
                y += spacing
            x += spacing

    def verlet_integrate(self):
        """Update positions using Verlet integration."""
        for p in self.particles:
            if p.fixed:
                continue

            # Calculate velocity from positions
            vx = (p.x - p.prev_x) * self.damping
            vy = (p.y - p.prev_y) * self.damping

            # Store current position
            p.prev_x = p.x
            p.prev_y = p.y

            # Update position
            p.x += vx
            p.y += vy

    def apply_gravity(self):
        """Apply downward gravitational force."""
        for p in self.particles:
            if not p.fixed:
                p.y += self.gravity

    def apply_attractor(self):
        """Apply attraction toward the attractor point."""
        if not self.attractor_active:
            return

        # Move attractor in a figure-8 pattern
        self.attractor_x = self.width / 2 + math.sin(self.time * 0.5) * self.width * 0.3
        self.attractor_y = self.height / 2 + math.sin(self.time) * self.height * 0.2

        for p in self.particles:
            if p.fixed:
                continue

            dx = self.attractor_x - p.x
            dy = self.attractor_y - p.y
            dist_sq = dx * dx + dy * dy + 0.1
            dist = math.sqrt(dist_sq)

            # Inverse square attraction with distance cap
            force = self.attraction_strength * p.mass / max(dist_sq, 1.0)
            force = min(force, 0.1)  # Cap maximum force

            p.x += dx / dist * force * 100
            p.y += dy / dist * force * 100

    def resolve_collisions(self):
        """Detect and resolve particle-particle collisions."""
        # Rebuild spatial hash
        self.spatial_hash.clear()
        for p in self.particles:
            self.spatial_hash.insert(p)

        # Check collisions using spatial hash
        for p1 in self.particles:
            nearby = self.spatial_hash.get_nearby(p1)
            for p2 in nearby:
                if p1 is p2:
                    continue

                dx = p2.x - p1.x
                dy = p2.y - p1.y
                dist_sq = dx * dx + dy * dy
                min_dist = p1.radius + p2.radius

                if dist_sq < min_dist * min_dist and dist_sq > 0:
                    dist = math.sqrt(dist_sq)
                    overlap = min_dist - dist

                    # Normalize collision vector
                    nx = dx / dist
                    ny = dy / dist

                    # Mass-weighted separation
                    total_mass = p1.mass + p2.mass
                    p1_ratio = p2.mass / total_mass
                    p2_ratio = p1.mass / total_mass

                    # Separate particles
                    if not p1.fixed:
                        p1.x -= nx * overlap * p1_ratio * 0.5
                        p1.y -= ny * overlap * p1_ratio * 0.5
                    if not p2.fixed:
                        p2.x += nx * overlap * p2_ratio * 0.5
                        p2.y += ny * overlap * p2_ratio * 0.5

    def resolve_boundaries(self):
        """Keep particles within bounds with bouncing."""
        margin = 1.0
        for p in self.particles:
            if p.fixed:
                continue

            # Left/Right boundaries
            if p.x < margin:
                p.x = margin
                p.prev_x = p.x + (p.x - p.prev_x) * self.collision_damping
            elif p.x > self.width - margin:
                p.x = self.width - margin
                p.prev_x = p.x + (p.x - p.prev_x) * self.collision_damping

            # Top/Bottom boundaries
            if p.y < margin:
                p.y = margin
                p.prev_y = p.y + (p.y - p.prev_y) * self.collision_damping
            elif p.y > self.height - margin:
                p.y = self.height - margin
                p.prev_y = p.y + (p.y - p.prev_y) * self.collision_damping

    def step(self, dt: float = 1.0):
        """Advance simulation by one timestep."""
        self.time += dt * 0.05

        self.apply_gravity()
        self.apply_attractor()
        self.verlet_integrate()

        # Multiple collision iterations for stability
        for _ in range(3):
            self.resolve_collisions()
            self.resolve_boundaries()

    def render(self) -> str:
        """Render the simulation to a string buffer."""
        # Create empty buffer
        buffer = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        color_buffer = [['' for _ in range(self.width)] for _ in range(self.height)]

        # Render attractor
        ax, ay = int(self.attractor_x), int(self.attractor_y)
        if 0 <= ax < self.width and 0 <= ay < self.height:
            buffer[ay][ax] = '✦'
            color_buffer[ay][ax] = '\033[1;35m'  # Magenta

        # Render particles
        for p in self.particles:
            x, y = int(p.x), int(p.y)
            if 0 <= x < self.width and 0 <= y < self.height:
                # Color based on velocity
                speed = p.speed
                color_idx = min(int(speed * 8), len(COLORS) - 1)

                # Character based on mass
                char_idx = min(int(p.mass), len(PARTICLE_CHARS) - 1)

                buffer[y][x] = PARTICLE_CHARS[char_idx]
                color_buffer[y][x] = COLORS[color_idx]

        # Build output string
        lines = []
        for y in range(self.height):
            line_parts = []
            for x in range(self.width):
                if color_buffer[y][x]:
                    line_parts.append(f"{color_buffer[y][x]}{buffer[y][x]}{RESET}")
                else:
                    line_parts.append(buffer[y][x])
            lines.append(''.join(line_parts))

        return '\n'.join(lines)


def print_header(width: int):
    """Print the simulation header."""
    print("\033[2J\033[H")  # Clear screen
    title = "◆ PARTICLE UNIVERSE ◆"
    subtitle = "Verlet Integration • Spatial Hashing • Gravitational Dynamics"
    print(f"\033[1;36m{'═' * width}\033[0m")
    print(f"\033[1;33m{title:^{width}}\033[0m")
    print(f"\033[0;37m{subtitle:^{width}}\033[0m")
    print(f"\033[1;36m{'═' * width}\033[0m")


def main():
    """Main simulation loop."""
    # Get terminal size
    try:
        term_size = os.get_terminal_size()
        width = min(term_size.columns - 1, 120)
        height = min(term_size.lines - 8, 35)
    except OSError:
        width, height = 80, 25

    # Initialize universe
    universe = ParticleUniverse(width, height)

    # Create initial particle configurations
    universe.spawn_spiral(width / 2, height / 2, count=40)
    universe.spawn_explosion(width / 4, height / 2, count=25)
    universe.spawn_explosion(3 * width / 4, height / 2, count=25)

    print_header(width)
    print("\033[0;90mWatching particles dance... Press Ctrl+C to exit\033[0m\n")
    time.sleep(1)

    frame_count = 0
    start_time = time.time()
    spawn_timer = 0

    try:
        while True:
            frame_start = time.time()

            # Periodically spawn new particles
            spawn_timer += 1
            if spawn_timer > 100 and len(universe.particles) < 200:
                spawn_timer = 0
                spawn_type = random.choice(['explosion', 'spiral', 'grid'])
                x = random.uniform(width * 0.2, width * 0.8)
                y = random.uniform(height * 0.2, height * 0.8)

                if spawn_type == 'explosion':
                    universe.spawn_explosion(x, y, count=15)
                elif spawn_type == 'spiral':
                    universe.spawn_spiral(x, y, count=20)
                else:
                    universe.spawn_grid(x - 5, y - 5, x + 5, y + 5, spacing=2.5)

            # Remove particles that are too old (keep simulation fresh)
            if len(universe.particles) > 250:
                universe.particles = universe.particles[-200:]

            # Physics step
            universe.step()

            # Render
            frame = universe.render()
            sys.stdout.write("\033[H")  # Move to top
            sys.stdout.write(frame)

            # Stats
            frame_count += 1
            elapsed = time.time() - frame_start
            fps = 1.0 / elapsed if elapsed > 0 else 0
            total_ke = sum(0.5 * p.mass * p.speed ** 2 for p in universe.particles)

            stats = (
                f"\n\033[1;32mParticles: {len(universe.particles):3d} │ "
                f"FPS: {fps:5.1f} │ "
                f"Energy: {total_ke:8.2f} │ "
                f"Frame: {frame_count}\033[0m"
            )
            sys.stdout.write(stats)
            sys.stdout.flush()

            # Target ~30 FPS
            sleep_time = max(0, 0.033 - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        print(f"\n\n\033[1;36m{'═' * width}\033[0m")
        print(f"\033[1;33mSimulation Complete!\033[0m")
        print(f"\033[0;37mTotal frames: {frame_count} | Average FPS: {avg_fps:.1f} | Runtime: {total_time:.1f}s\033[0m")
        print(f"\033[1;36m{'═' * width}\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
