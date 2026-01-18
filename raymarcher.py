#!/usr/bin/env python3
"""
Terminal 3D Raymarching Engine
==============================
A real-time ASCII renderer featuring:
- Signed Distance Function (SDF) geometry
- Soft shadows and ambient occlusion
- Reflections on metallic surfaces
- Procedural animation
- Physically-based lighting model

Author: Claude (Opus 4.5)
"""

import math
import time
import sys
import os
from dataclasses import dataclass
from typing import Tuple, Callable

# ASCII gradient for rendering depth and lighting
ASCII_GRADIENT = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

@dataclass
class Vec3:
    """3D Vector with full mathematical operations."""
    x: float
    y: float
    z: float

    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> 'Vec3':
        return self.__mul__(scalar)

    def __neg__(self) -> 'Vec3':
        return Vec3(-self.x, -self.y, -self.z)

    def dot(self, other: 'Vec3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vec3') -> 'Vec3':
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def length(self) -> float:
        return math.sqrt(self.dot(self))

    def normalize(self) -> 'Vec3':
        l = self.length()
        if l == 0:
            return Vec3(0, 0, 0)
        return self * (1.0 / l)

    def reflect(self, normal: 'Vec3') -> 'Vec3':
        return self - normal * (2.0 * self.dot(normal))

    def abs(self) -> 'Vec3':
        return Vec3(abs(self.x), abs(self.y), abs(self.z))

    def max_component(self) -> float:
        return max(self.x, self.y, self.z)


@dataclass
class Material:
    """Surface material properties."""
    color: Vec3
    reflectivity: float = 0.0
    emission: float = 0.0


@dataclass
class HitInfo:
    """Information about a ray-surface intersection."""
    distance: float
    material: Material


class Scene:
    """
    The 3D scene containing all geometry defined via Signed Distance Functions (SDFs).
    SDFs return the distance from a point to the nearest surface.
    """

    def __init__(self, time: float = 0.0):
        self.time = time

    # === Primitive SDF Operations ===

    @staticmethod
    def sdf_sphere(p: Vec3, center: Vec3, radius: float) -> float:
        return (p - center).length() - radius

    @staticmethod
    def sdf_box(p: Vec3, center: Vec3, size: Vec3) -> float:
        d = (p - center).abs() - size
        return Vec3(max(d.x, 0), max(d.y, 0), max(d.z, 0)).length() + min(d.max_component(), 0)

    @staticmethod
    def sdf_torus(p: Vec3, center: Vec3, major_r: float, minor_r: float) -> float:
        pc = p - center
        q = Vec3(math.sqrt(pc.x * pc.x + pc.z * pc.z) - major_r, pc.y, 0)
        return math.sqrt(q.x * q.x + q.y * q.y) - minor_r

    @staticmethod
    def sdf_cylinder(p: Vec3, center: Vec3, radius: float, height: float) -> float:
        pc = p - center
        d = Vec3(math.sqrt(pc.x * pc.x + pc.z * pc.z) - radius, abs(pc.y) - height, 0)
        return min(max(d.x, d.y), 0.0) + Vec3(max(d.x, 0), max(d.y, 0), 0).length()

    @staticmethod
    def sdf_plane(p: Vec3, normal: Vec3, offset: float) -> float:
        return p.dot(normal) + offset

    # === SDF Boolean Operations ===

    @staticmethod
    def op_union(d1: float, d2: float) -> float:
        return min(d1, d2)

    @staticmethod
    def op_subtract(d1: float, d2: float) -> float:
        return max(d1, -d2)

    @staticmethod
    def op_intersect(d1: float, d2: float) -> float:
        return max(d1, d2)

    @staticmethod
    def op_smooth_union(d1: float, d2: float, k: float) -> float:
        h = max(k - abs(d1 - d2), 0.0) / k
        return min(d1, d2) - h * h * k * 0.25

    # === Scene Definition ===

    def get_scene_sdf(self, p: Vec3) -> HitInfo:
        """
        Define the entire scene geometry and materials.
        Returns distance to nearest surface and its material.
        """
        t = self.time

        # Animated floating sphere
        sphere_y = 1.0 + 0.5 * math.sin(t * 2.0)
        sphere_x = 2.0 * math.sin(t * 0.7)
        sphere1 = self.sdf_sphere(p, Vec3(sphere_x, sphere_y, 0), 0.8)
        mat_sphere1 = Material(Vec3(1.0, 0.3, 0.2), reflectivity=0.6)

        # Rotating torus
        rot_angle = t * 0.5
        torus_center = Vec3(-1.5, 0.8 + 0.3 * math.sin(t * 1.5), 1.5)
        # Rotate point around Y axis for torus rotation
        cos_a, sin_a = math.cos(rot_angle), math.sin(rot_angle)
        p_rot = Vec3(
            (p.x - torus_center.x) * cos_a - (p.z - torus_center.z) * sin_a + torus_center.x,
            p.y,
            (p.x - torus_center.x) * sin_a + (p.z - torus_center.z) * cos_a + torus_center.z
        )
        torus = self.sdf_torus(p_rot, torus_center, 0.6, 0.2)
        mat_torus = Material(Vec3(0.2, 0.8, 0.3), reflectivity=0.4)

        # Morphing box-sphere (demonstrates smooth union)
        morph_center = Vec3(1.5, 0.6, 2.0)
        morph_factor = 0.5 + 0.5 * math.sin(t * 1.2)
        box = self.sdf_box(p, morph_center, Vec3(0.4, 0.4, 0.4))
        sphere_morph = self.sdf_sphere(p, morph_center, 0.5)
        morphed = box * morph_factor + sphere_morph * (1.0 - morph_factor)
        mat_morph = Material(Vec3(0.3, 0.4, 1.0), reflectivity=0.5)

        # Pulsating cylinder
        cyl_radius = 0.3 + 0.1 * math.sin(t * 3.0)
        cylinder = self.sdf_cylinder(p, Vec3(0, 0.5, 3.0), cyl_radius, 0.5)
        mat_cyl = Material(Vec3(1.0, 0.8, 0.2), reflectivity=0.3)

        # Ground plane (reflective)
        ground = self.sdf_plane(p, Vec3(0, 1, 0), 0.0)
        # Checkerboard pattern
        checker = (int(math.floor(p.x) + math.floor(p.z)) % 2 == 0)
        mat_ground = Material(
            Vec3(0.9, 0.9, 0.9) if checker else Vec3(0.2, 0.2, 0.2),
            reflectivity=0.8
        )

        # Combine all objects
        result_dist = ground
        result_mat = mat_ground

        for dist, mat in [
            (sphere1, mat_sphere1),
            (torus, mat_torus),
            (morphed, mat_morph),
            (cylinder, mat_cyl)
        ]:
            if dist < result_dist:
                result_dist = dist
                result_mat = mat

        return HitInfo(result_dist, result_mat)

    def get_normal(self, p: Vec3) -> Vec3:
        """Calculate surface normal using gradient of SDF."""
        eps = 0.001
        d = self.get_scene_sdf(p).distance
        return Vec3(
            self.get_scene_sdf(Vec3(p.x + eps, p.y, p.z)).distance - d,
            self.get_scene_sdf(Vec3(p.x, p.y + eps, p.z)).distance - d,
            self.get_scene_sdf(Vec3(p.x, p.y, p.z + eps)).distance - d
        ).normalize()


class Raymarcher:
    """
    The raymarching renderer with advanced lighting features.
    """

    MAX_STEPS = 64
    MAX_DIST = 50.0
    SURF_DIST = 0.001

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.aspect = width / (height * 2.0)  # Account for character aspect ratio

        # Camera setup
        self.camera_pos = Vec3(0, 2, -6)
        self.camera_target = Vec3(0, 1, 0)

        # Lighting
        self.light_dir = Vec3(0.5, 0.8, -0.6).normalize()
        self.ambient = 0.15

    def raymarch(self, origin: Vec3, direction: Vec3, scene: Scene) -> Tuple[float, Material]:
        """
        March a ray through the scene until it hits a surface or escapes.
        """
        total_dist = 0.0

        for _ in range(self.MAX_STEPS):
            current_pos = origin + direction * total_dist
            hit = scene.get_scene_sdf(current_pos)

            if hit.distance < self.SURF_DIST:
                return total_dist, hit.material

            if total_dist > self.MAX_DIST:
                break

            total_dist += hit.distance

        return self.MAX_DIST, Material(Vec3(0.1, 0.1, 0.2))  # Sky color

    def soft_shadow(self, origin: Vec3, direction: Vec3, scene: Scene, k: float = 16.0) -> float:
        """
        Calculate soft shadows using penumbra estimation.
        """
        result = 1.0
        t = 0.02  # Start slightly away from surface

        for _ in range(32):
            pos = origin + direction * t
            h = scene.get_scene_sdf(pos).distance

            if h < 0.001:
                return 0.0

            result = min(result, k * h / t)
            t += h

            if t > 10.0:
                break

        return max(result, 0.0)

    def ambient_occlusion(self, pos: Vec3, normal: Vec3, scene: Scene) -> float:
        """
        Estimate ambient occlusion by sampling nearby geometry.
        """
        occ = 0.0
        scale = 1.0

        for i in range(5):
            h = 0.01 + 0.12 * i
            d = scene.get_scene_sdf(pos + normal * h).distance
            occ += (h - d) * scale
            scale *= 0.95

        return max(1.0 - 3.0 * occ, 0.0)

    def shade(self, pos: Vec3, normal: Vec3, material: Material,
              view_dir: Vec3, scene: Scene, depth: int = 0) -> float:
        """
        Calculate lighting with shadows, AO, and reflections.
        """
        # Diffuse lighting
        ndotl = max(normal.dot(self.light_dir), 0.0)

        # Soft shadows
        shadow = self.soft_shadow(
            pos + normal * 0.02,
            self.light_dir,
            scene
        )

        # Ambient occlusion
        ao = self.ambient_occlusion(pos, normal, scene)

        # Specular highlight (Blinn-Phong)
        half_vec = (self.light_dir - view_dir).normalize()
        spec = pow(max(normal.dot(half_vec), 0.0), 32.0)

        # Combine lighting
        diffuse = ndotl * shadow
        lighting = self.ambient * ao + diffuse * 0.7 + spec * shadow * 0.3

        # Reflections (recursive raymarching)
        if depth < 2 and material.reflectivity > 0.1:
            reflect_dir = view_dir.reflect(normal)
            reflect_origin = pos + normal * 0.02
            ref_dist, ref_mat = self.raymarch(reflect_origin, reflect_dir, scene)

            if ref_dist < self.MAX_DIST:
                ref_pos = reflect_origin + reflect_dir * ref_dist
                ref_normal = scene.get_normal(ref_pos)
                ref_light = self.shade(ref_pos, ref_normal, ref_mat, reflect_dir, scene, depth + 1)
                lighting = lighting * (1.0 - material.reflectivity) + ref_light * material.reflectivity

        return lighting

    def render_frame(self, scene: Scene) -> str:
        """
        Render a complete frame as ASCII art.
        """
        # Calculate camera basis vectors
        forward = (self.camera_target - self.camera_pos).normalize()
        right = forward.cross(Vec3(0, 1, 0)).normalize()
        up = right.cross(forward)

        frame = []

        for y in range(self.height):
            row = []
            for x in range(self.width):
                # Convert pixel to normalized device coordinates
                u = (2.0 * x / self.width - 1.0) * self.aspect
                v = 1.0 - 2.0 * y / self.height

                # Calculate ray direction
                ray_dir = (forward + right * u + up * v).normalize()

                # Raymarch
                dist, material = self.raymarch(self.camera_pos, ray_dir, scene)

                if dist < self.MAX_DIST:
                    # Hit something - calculate lighting
                    hit_pos = self.camera_pos + ray_dir * dist
                    normal = scene.get_normal(hit_pos)
                    brightness = self.shade(hit_pos, normal, material, ray_dir, scene)

                    # Apply material color influence
                    color_intensity = (material.color.x + material.color.y + material.color.z) / 3.0
                    brightness *= 0.5 + 0.5 * color_intensity
                else:
                    # Sky gradient
                    brightness = 0.1 + 0.1 * (1.0 - y / self.height)

                # Map brightness to ASCII character
                brightness = max(0.0, min(1.0, brightness))
                char_idx = int(brightness * (len(ASCII_GRADIENT) - 1))
                row.append(ASCII_GRADIENT[char_idx])

            frame.append(''.join(row))

        return '\n'.join(frame)


def main():
    """
    Main animation loop with smooth timing.
    """
    # Get terminal size
    try:
        term_size = os.get_terminal_size()
        width = min(term_size.columns, 120)
        height = min(term_size.lines - 2, 40)
    except OSError:
        width, height = 80, 30

    renderer = Raymarcher(width, height)

    # Print header
    print("\033[2J\033[H")  # Clear screen
    print(f"\033[1;36m{'=' * width}\033[0m")
    print(f"\033[1;33m{'Terminal 3D Raymarching Engine':^{width}}\033[0m")
    print(f"\033[1;36m{'=' * width}\033[0m")
    print(f"\033[0;37m{'Featuring: SDFs, Soft Shadows, AO, Reflections':^{width}}\033[0m")
    print(f"\033[1;36m{'=' * width}\033[0m")
    print("\033[0;90mPress Ctrl+C to exit\033[0m\n")

    time.sleep(2)

    start_time = time.time()
    frame_count = 0

    try:
        while True:
            frame_start = time.time()
            current_time = frame_start - start_time

            # Create scene with current time for animation
            scene = Scene(current_time)

            # Animate camera in a gentle orbit
            orbit_radius = 7.0
            orbit_speed = 0.2
            renderer.camera_pos = Vec3(
                orbit_radius * math.sin(current_time * orbit_speed),
                2.5 + 0.5 * math.sin(current_time * 0.3),
                -orbit_radius * math.cos(current_time * orbit_speed)
            )

            # Render and display
            frame = renderer.render_frame(scene)

            # Move cursor to top and draw
            sys.stdout.write("\033[H")
            sys.stdout.write(frame)

            frame_count += 1
            elapsed = time.time() - frame_start
            fps = 1.0 / elapsed if elapsed > 0 else 0

            # Status line
            sys.stdout.write(f"\n\033[1;32mFPS: {fps:.1f} | Time: {current_time:.1f}s | Frame: {frame_count}\033[0m")
            sys.stdout.flush()

            # Cap framerate
            sleep_time = max(0, 0.033 - elapsed)  # ~30 FPS target
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\n\033[1;36mThanks for watching! Total frames rendered: {}\033[0m".format(frame_count))
        sys.exit(0)


if __name__ == "__main__":
    main()
