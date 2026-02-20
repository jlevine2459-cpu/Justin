"""Tests for Particle physics and SpatialHash collision detection.

Coverage target: particle_universe.py lines 52-354
Priority: HIGH — Physics simulation correctness depends on Verlet
integration accuracy, proper collision detection, and boundary enforcement.
"""
import math
import pytest
from particle_universe import Particle, SpatialHash, ParticleUniverse


class TestParticle:
    """Particle dataclass and Verlet velocity properties."""

    def test_default_prev_position(self):
        p = Particle(x=5.0, y=10.0)
        assert p.prev_x == 5.0
        assert p.prev_y == 10.0

    def test_explicit_prev_position(self):
        p = Particle(x=5.0, y=10.0, prev_x=4.0, prev_y=9.0)
        assert p.prev_x == 4.0
        assert p.prev_y == 9.0

    def test_velocity_at_rest(self):
        p = Particle(x=5.0, y=5.0)
        assert p.vx == 0.0
        assert p.vy == 0.0

    def test_velocity_moving(self):
        p = Particle(x=5.0, y=10.0, prev_x=3.0, prev_y=8.0)
        assert p.vx == 2.0
        assert p.vy == 2.0

    def test_speed_at_rest(self):
        p = Particle(x=0, y=0)
        assert p.speed == 0.0

    def test_speed_moving(self):
        p = Particle(x=3.0, y=4.0, prev_x=0.0, prev_y=0.0)
        assert p.speed == pytest.approx(5.0)

    def test_apply_force(self):
        p = Particle(x=0.0, y=0.0, mass=2.0)
        p.apply_force(4.0, 0.0, dt=1.0)
        # a = F/m = 4/2 = 2, displacement = a*dt^2 = 2
        assert p.x == pytest.approx(2.0)
        assert p.y == pytest.approx(0.0)

    def test_apply_force_with_mass(self):
        light = Particle(x=0.0, y=0.0, mass=1.0)
        heavy = Particle(x=0.0, y=0.0, mass=10.0)
        light.apply_force(10.0, 0.0)
        heavy.apply_force(10.0, 0.0)
        # Lighter particle should accelerate more
        assert light.x > heavy.x

    def test_fixed_particle_default(self):
        p = Particle(x=0, y=0)
        assert p.fixed is False


class TestSpatialHash:
    """Spatial hashing for O(1) neighbor lookups."""

    def test_insert_and_retrieve(self):
        sh = SpatialHash(cell_size=3.0)
        p = Particle(x=1.0, y=1.0)
        sh.insert(p)
        nearby = sh.get_nearby(p)
        assert p in nearby

    def test_nearby_particles_same_cell(self):
        sh = SpatialHash(cell_size=10.0)
        p1 = Particle(x=1.0, y=1.0)
        p2 = Particle(x=2.0, y=2.0)
        sh.insert(p1)
        sh.insert(p2)
        nearby = sh.get_nearby(p1)
        assert p1 in nearby
        assert p2 in nearby

    def test_nearby_particles_adjacent_cell(self):
        sh = SpatialHash(cell_size=3.0)
        p1 = Particle(x=2.9, y=0.0)
        p2 = Particle(x=3.1, y=0.0)  # Just across cell boundary
        sh.insert(p1)
        sh.insert(p2)
        nearby = sh.get_nearby(p1)
        assert p2 in nearby

    def test_distant_particles_not_nearby(self):
        sh = SpatialHash(cell_size=3.0)
        p1 = Particle(x=0.0, y=0.0)
        p2 = Particle(x=100.0, y=100.0)
        sh.insert(p1)
        sh.insert(p2)
        nearby = sh.get_nearby(p1)
        assert p2 not in nearby

    def test_clear(self):
        sh = SpatialHash(cell_size=3.0)
        sh.insert(Particle(x=0, y=0))
        sh.clear()
        assert len(sh.grid) == 0

    def test_hash_deterministic(self):
        sh = SpatialHash(cell_size=5.0)
        h1 = sh._hash(7.0, 3.0)
        h2 = sh._hash(7.0, 3.0)
        assert h1 == h2

    def test_hash_negative_coordinates(self):
        sh = SpatialHash(cell_size=3.0)
        p = Particle(x=-5.0, y=-5.0)
        sh.insert(p)
        nearby = sh.get_nearby(p)
        assert p in nearby


class TestParticleUniverse:
    """Physics simulation engine integration tests."""

    def test_add_particle(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(10, 10)
        assert len(u.particles) == 1
        assert u.particles[0].x == 10
        assert u.particles[0].y == 10

    def test_add_particle_with_velocity(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(10, 10, vx=2, vy=3)
        p = u.particles[0]
        assert p.vx == pytest.approx(2.0)
        assert p.vy == pytest.approx(3.0)

    def test_spawn_explosion_count(self):
        u = ParticleUniverse(40, 20)
        u.spawn_explosion(20, 10, count=15)
        assert len(u.particles) == 15

    def test_spawn_explosion_centered(self):
        u = ParticleUniverse(40, 20)
        u.spawn_explosion(20, 10, count=50)
        # All particles start at same position
        for p in u.particles:
            assert p.x == 20
            assert p.y == 10

    def test_spawn_spiral_count(self):
        u = ParticleUniverse(80, 40)
        u.spawn_spiral(40, 20, count=30)
        assert len(u.particles) == 30

    def test_spawn_grid(self):
        u = ParticleUniverse(40, 20)
        u.spawn_grid(0, 0, 10, 10, spacing=5.0)
        # Grid from 0 to 10 with spacing 5: (0,0), (0,5), (0,10), (5,0), etc.
        assert len(u.particles) == 9  # 3x3 grid

    def test_gravity_pulls_down(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(20, 5)
        initial_y = u.particles[0].y
        u.apply_gravity()
        assert u.particles[0].y > initial_y

    def test_fixed_particles_ignore_gravity(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(20, 5)
        u.particles[0].fixed = True
        initial_y = u.particles[0].y
        u.apply_gravity()
        assert u.particles[0].y == initial_y

    def test_verlet_integrate_stationary(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(20, 10)
        u.verlet_integrate()
        # A stationary particle should remain roughly stationary
        assert u.particles[0].x == pytest.approx(20, abs=0.1)
        assert u.particles[0].y == pytest.approx(10, abs=0.1)

    def test_verlet_integrate_moving(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(20, 10, vx=1.0, vy=0.0)
        u.verlet_integrate()
        # Particle should have moved in x direction
        assert u.particles[0].x > 20

    def test_boundary_enforcement(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(-5, -5)  # Outside boundaries
        u.resolve_boundaries()
        p = u.particles[0]
        assert p.x >= 1.0  # margin
        assert p.y >= 1.0

    def test_boundary_right_bottom(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(50, 25)  # Outside right/bottom boundaries
        u.resolve_boundaries()
        p = u.particles[0]
        assert p.x <= 39.0  # width - margin
        assert p.y <= 19.0  # height - margin

    def test_step_advances_time(self):
        u = ParticleUniverse(40, 20)
        initial_time = u.time
        u.step()
        assert u.time > initial_time

    def test_render_produces_output(self):
        u = ParticleUniverse(20, 10)
        u.add_particle(10, 5)
        output = u.render()
        assert isinstance(output, str)
        lines = output.split('\n')
        assert len(lines) == 10

    def test_collision_detection_overlapping(self):
        u = ParticleUniverse(40, 20)
        u.add_particle(10, 10, radius=1.0)
        u.add_particle(10.5, 10, radius=1.0)
        u.resolve_collisions()
        # After resolution, particles should be further apart
        dx = abs(u.particles[1].x - u.particles[0].x)
        assert dx > 0.5  # Should have separated

    def test_attractor_moves(self):
        u = ParticleUniverse(40, 20)
        initial_x = u.attractor_x
        u.time = 1.0
        u.apply_attractor()
        # Attractor position is recalculated based on time
        # At time=1.0 it should have moved from center
        assert u.attractor_x != initial_x or u.attractor_y != u.height / 2
