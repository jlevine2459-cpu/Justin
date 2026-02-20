"""Tests for Scene SDF primitives and boolean operations.

Coverage target: raymarcher.py lines 91-220
Priority: HIGH — SDF correctness directly determines whether geometry
renders correctly. Wrong distances produce visual artifacts.
"""
import math
import pytest
from raymarcher import Vec3, Scene, Material, HitInfo, Raymarcher


class TestSDFSphere:
    """Signed distance function for spheres."""

    def test_point_on_surface(self):
        d = Scene.sdf_sphere(Vec3(1, 0, 0), Vec3(0, 0, 0), 1.0)
        assert d == pytest.approx(0.0)

    def test_point_inside(self):
        d = Scene.sdf_sphere(Vec3(0.5, 0, 0), Vec3(0, 0, 0), 1.0)
        assert d < 0

    def test_point_outside(self):
        d = Scene.sdf_sphere(Vec3(2, 0, 0), Vec3(0, 0, 0), 1.0)
        assert d == pytest.approx(1.0)

    def test_at_center(self):
        d = Scene.sdf_sphere(Vec3(0, 0, 0), Vec3(0, 0, 0), 1.0)
        assert d == pytest.approx(-1.0)

    def test_offset_center(self):
        d = Scene.sdf_sphere(Vec3(5, 0, 0), Vec3(3, 0, 0), 1.0)
        assert d == pytest.approx(1.0)


class TestSDFBox:
    """Signed distance function for axis-aligned boxes."""

    def test_point_on_surface(self):
        d = Scene.sdf_box(Vec3(1, 0, 0), Vec3(0, 0, 0), Vec3(1, 1, 1))
        assert d == pytest.approx(0.0)

    def test_point_inside(self):
        d = Scene.sdf_box(Vec3(0, 0, 0), Vec3(0, 0, 0), Vec3(1, 1, 1))
        assert d < 0

    def test_point_outside_face(self):
        d = Scene.sdf_box(Vec3(2, 0, 0), Vec3(0, 0, 0), Vec3(1, 1, 1))
        assert d == pytest.approx(1.0)

    def test_point_outside_corner(self):
        # Distance from corner of unit box to point at (2,2,2)
        d = Scene.sdf_box(Vec3(2, 2, 2), Vec3(0, 0, 0), Vec3(1, 1, 1))
        assert d == pytest.approx(math.sqrt(3))


class TestSDFTorus:
    """Signed distance function for torus."""

    def test_point_on_outer_rim(self):
        # Major radius 2, minor radius 0.5, point on outer edge in XZ plane
        d = Scene.sdf_torus(Vec3(2.5, 0, 0), Vec3(0, 0, 0), 2.0, 0.5)
        assert d == pytest.approx(0.0, abs=1e-6)

    def test_point_on_inner_rim(self):
        d = Scene.sdf_torus(Vec3(1.5, 0, 0), Vec3(0, 0, 0), 2.0, 0.5)
        assert d == pytest.approx(0.0, abs=1e-6)

    def test_point_at_center(self):
        d = Scene.sdf_torus(Vec3(0, 0, 0), Vec3(0, 0, 0), 2.0, 0.5)
        assert d > 0  # Center of torus is outside the surface


class TestSDFCylinder:
    """Signed distance function for cylinders."""

    def test_point_on_side_surface(self):
        d = Scene.sdf_cylinder(Vec3(1, 0, 0), Vec3(0, 0, 0), 1.0, 1.0)
        assert d == pytest.approx(0.0, abs=1e-6)

    def test_point_inside(self):
        d = Scene.sdf_cylinder(Vec3(0, 0, 0), Vec3(0, 0, 0), 1.0, 1.0)
        assert d < 0

    def test_point_outside(self):
        d = Scene.sdf_cylinder(Vec3(3, 0, 0), Vec3(0, 0, 0), 1.0, 1.0)
        assert d > 0


class TestSDFPlane:
    """Signed distance function for infinite planes."""

    def test_horizontal_plane_above(self):
        d = Scene.sdf_plane(Vec3(0, 1, 0), Vec3(0, 1, 0), 0.0)
        assert d == pytest.approx(1.0)

    def test_horizontal_plane_on_surface(self):
        d = Scene.sdf_plane(Vec3(0, 0, 0), Vec3(0, 1, 0), 0.0)
        assert d == pytest.approx(0.0)

    def test_horizontal_plane_below(self):
        d = Scene.sdf_plane(Vec3(0, -1, 0), Vec3(0, 1, 0), 0.0)
        assert d == pytest.approx(-1.0)

    def test_offset_plane(self):
        d = Scene.sdf_plane(Vec3(0, 0, 0), Vec3(0, 1, 0), 5.0)
        assert d == pytest.approx(5.0)


class TestBooleanOperations:
    """CSG boolean operations on distance fields."""

    def test_union_returns_min(self):
        assert Scene.op_union(1.0, 2.0) == 1.0
        assert Scene.op_union(3.0, -1.0) == -1.0

    def test_subtract(self):
        assert Scene.op_subtract(1.0, 2.0) == max(1.0, -2.0)
        assert Scene.op_subtract(-0.5, -1.0) == max(-0.5, 1.0)

    def test_intersect_returns_max(self):
        assert Scene.op_intersect(1.0, 2.0) == 2.0
        assert Scene.op_intersect(-1.0, 0.5) == 0.5

    def test_smooth_union_blends(self):
        # Smooth union should be <= min(d1, d2)
        result = Scene.op_smooth_union(1.0, 1.0, k=0.5)
        assert result <= min(1.0, 1.0)

    def test_smooth_union_far_apart_equals_union(self):
        # When objects are far apart, smooth union ≈ regular union
        result = Scene.op_smooth_union(10.0, 20.0, k=0.5)
        assert result == pytest.approx(10.0, abs=0.01)


class TestSceneComposite:
    """Integration test for the full scene SDF."""

    def test_get_scene_sdf_returns_hitinfo(self):
        scene = Scene(time=0.0)
        hit = scene.get_scene_sdf(Vec3(0, 5, 0))
        assert isinstance(hit, HitInfo)
        assert isinstance(hit.distance, float)
        assert isinstance(hit.material, Material)

    def test_ground_plane_at_origin(self):
        scene = Scene(time=0.0)
        hit = scene.get_scene_sdf(Vec3(0, 0, 0))
        # Ground plane is at y=0, so distance should be ~0 at y=0
        assert hit.distance == pytest.approx(0.0, abs=0.1)

    def test_far_above_scene(self):
        scene = Scene(time=0.0)
        hit = scene.get_scene_sdf(Vec3(0, 100, 0))
        # Far above — nearest surface should be ground plane at y=0
        assert hit.distance > 50

    def test_get_normal_ground_plane(self):
        scene = Scene(time=0.0)
        # Normal at a point on the ground plane should point up
        normal = scene.get_normal(Vec3(10, 0, 10))
        assert normal.y == pytest.approx(1.0, abs=0.1)


class TestRaymarcher:
    """Tests for the raymarching renderer."""

    def test_ray_hits_surface(self):
        renderer = Raymarcher(20, 10)
        scene = Scene(time=0.0)
        # Shoot ray downward — should hit ground or a scene object
        origin = Vec3(0, 5, 0)
        direction = Vec3(0, -1, 0).normalize()
        dist, mat = renderer.raymarch(origin, direction, scene)
        assert dist < renderer.MAX_DIST
        assert dist > 0

    def test_ray_escapes_upward(self):
        renderer = Raymarcher(20, 10)
        scene = Scene(time=0.0)
        # Shoot ray straight up — should escape (no ceiling)
        origin = Vec3(0, 5, 0)
        direction = Vec3(0, 1, 0).normalize()
        dist, _ = renderer.raymarch(origin, direction, scene)
        assert dist >= renderer.MAX_DIST

    def test_render_frame_returns_string(self):
        renderer = Raymarcher(10, 5)
        scene = Scene(time=0.0)
        frame = renderer.render_frame(scene)
        assert isinstance(frame, str)
        lines = frame.split('\n')
        assert len(lines) == 5

    def test_render_frame_correct_width(self):
        width, height = 15, 5
        renderer = Raymarcher(width, height)
        scene = Scene(time=0.0)
        frame = renderer.render_frame(scene)
        lines = frame.split('\n')
        for line in lines:
            assert len(line) == width

    def test_ambient_occlusion_range(self):
        renderer = Raymarcher(20, 10)
        scene = Scene(time=0.0)
        pos = Vec3(10, 0, 10)
        normal = Vec3(0, 1, 0)
        ao = renderer.ambient_occlusion(pos, normal, scene)
        assert 0.0 <= ao <= 1.0

    def test_soft_shadow_range(self):
        renderer = Raymarcher(20, 10)
        scene = Scene(time=0.0)
        pos = Vec3(0, 5, 0)
        direction = Vec3(0.5, 0.8, -0.6).normalize()
        shadow = renderer.soft_shadow(pos, direction, scene)
        assert 0.0 <= shadow <= 1.0
