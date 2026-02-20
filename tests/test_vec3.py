"""Tests for Vec3 3D vector math operations.

Coverage target: raymarcher.py lines 26-73
Priority: HIGH — Vec3 is the foundational data type used by the entire
raymarching engine. Bugs here cascade through all rendering calculations.
"""
import math
import pytest
from raymarcher import Vec3


class TestVec3Arithmetic:
    """Basic arithmetic operations on 3D vectors."""

    def test_add(self):
        result = Vec3(1, 2, 3) + Vec3(4, 5, 6)
        assert result.x == 5
        assert result.y == 7
        assert result.z == 9

    def test_add_negative(self):
        result = Vec3(1, -2, 3) + Vec3(-4, 5, -6)
        assert result.x == -3
        assert result.y == 3
        assert result.z == -3

    def test_sub(self):
        result = Vec3(5, 7, 9) - Vec3(1, 2, 3)
        assert result.x == 4
        assert result.y == 5
        assert result.z == 6

    def test_mul_scalar(self):
        result = Vec3(1, 2, 3) * 2
        assert result.x == 2
        assert result.y == 4
        assert result.z == 6

    def test_rmul_scalar(self):
        result = 3 * Vec3(1, 2, 3)
        assert result.x == 3
        assert result.y == 6
        assert result.z == 9

    def test_neg(self):
        result = -Vec3(1, -2, 3)
        assert result.x == -1
        assert result.y == 2
        assert result.z == -3

    def test_mul_by_zero(self):
        result = Vec3(5, 10, 15) * 0
        assert result.x == 0
        assert result.y == 0
        assert result.z == 0


class TestVec3Products:
    """Dot product and cross product tests."""

    def test_dot_product_orthogonal(self):
        assert Vec3(1, 0, 0).dot(Vec3(0, 1, 0)) == 0

    def test_dot_product_parallel(self):
        assert Vec3(1, 0, 0).dot(Vec3(1, 0, 0)) == 1

    def test_dot_product_antiparallel(self):
        assert Vec3(1, 0, 0).dot(Vec3(-1, 0, 0)) == -1

    def test_dot_product_general(self):
        assert Vec3(1, 2, 3).dot(Vec3(4, 5, 6)) == 32

    def test_cross_product_i_cross_j(self):
        result = Vec3(1, 0, 0).cross(Vec3(0, 1, 0))
        assert result.x == 0
        assert result.y == 0
        assert result.z == 1

    def test_cross_product_j_cross_i(self):
        result = Vec3(0, 1, 0).cross(Vec3(1, 0, 0))
        assert result.x == 0
        assert result.y == 0
        assert result.z == -1

    def test_cross_product_parallel_is_zero(self):
        result = Vec3(1, 0, 0).cross(Vec3(2, 0, 0))
        assert result.x == 0
        assert result.y == 0
        assert result.z == 0

    def test_cross_product_anticommutative(self):
        a = Vec3(1, 2, 3)
        b = Vec3(4, 5, 6)
        ab = a.cross(b)
        ba = b.cross(a)
        assert ab.x == pytest.approx(-ba.x)
        assert ab.y == pytest.approx(-ba.y)
        assert ab.z == pytest.approx(-ba.z)


class TestVec3Geometry:
    """Length, normalization, reflection, and component ops."""

    def test_length_unit(self):
        assert Vec3(1, 0, 0).length() == 1.0

    def test_length_general(self):
        assert Vec3(3, 4, 0).length() == pytest.approx(5.0)

    def test_length_3d(self):
        assert Vec3(1, 2, 2).length() == pytest.approx(3.0)

    def test_length_zero_vector(self):
        assert Vec3(0, 0, 0).length() == 0.0

    def test_normalize_unit_vector(self):
        n = Vec3(1, 0, 0).normalize()
        assert n.length() == pytest.approx(1.0)

    def test_normalize_general(self):
        n = Vec3(3, 4, 0).normalize()
        assert n.x == pytest.approx(0.6)
        assert n.y == pytest.approx(0.8)
        assert n.z == pytest.approx(0.0)
        assert n.length() == pytest.approx(1.0)

    def test_normalize_zero_vector(self):
        n = Vec3(0, 0, 0).normalize()
        assert n.x == 0
        assert n.y == 0
        assert n.z == 0

    def test_reflect_perpendicular(self):
        # Light coming straight down, reflecting off horizontal surface
        incoming = Vec3(0, -1, 0)
        normal = Vec3(0, 1, 0)
        reflected = incoming.reflect(normal)
        assert reflected.x == pytest.approx(0)
        assert reflected.y == pytest.approx(1)
        assert reflected.z == pytest.approx(0)

    def test_reflect_45_degrees(self):
        incoming = Vec3(1, -1, 0).normalize()
        normal = Vec3(0, 1, 0)
        reflected = incoming.reflect(normal)
        expected = Vec3(1, 1, 0).normalize()
        assert reflected.x == pytest.approx(expected.x)
        assert reflected.y == pytest.approx(expected.y)

    def test_abs(self):
        result = Vec3(-1, -2, 3).abs()
        assert result.x == 1
        assert result.y == 2
        assert result.z == 3

    def test_max_component(self):
        assert Vec3(1, 5, 3).max_component() == 5
        assert Vec3(-1, -5, -3).max_component() == -1


class TestVec3EdgeCases:
    """Edge cases and numerical stability."""

    def test_very_small_vector_normalize(self):
        tiny = Vec3(1e-10, 0, 0)
        n = tiny.normalize()
        assert n.length() == pytest.approx(1.0)

    def test_large_vector_normalize(self):
        big = Vec3(1e10, 0, 0)
        n = big.normalize()
        assert n.length() == pytest.approx(1.0)

    def test_identity_operations(self):
        v = Vec3(3, 4, 5)
        zero = Vec3(0, 0, 0)
        result = v + zero
        assert result.x == v.x
        assert result.y == v.y
        assert result.z == v.z
