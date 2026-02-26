# RubiksCube3D.py

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math
from RubiksCubeCore import RubiksCubeCore
from Scrambler import CubeScrambler
from Solver import CubeSolver

# Quaternion Helpers 

def quat_multiply(q1, q2):
    """Hamilton product of two quaternions [w, x, y, z]."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ])

def quat_normalize(q):
    """Normalize a quaternion to unit length."""
    n = np.linalg.norm(q)
    if n < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return q / n

def quat_to_matrix(q):
    """Convert unit quaternion [w,x,y,z] to a 4x4 rotation matrix (column-major for OpenGL)."""
    w, x, y, z = q
    return np.array([
        [1 - 2*(y*y + z*z),     2*(x*y + w*z),     2*(x*z - w*y), 0],
        [    2*(x*y - w*z), 1 - 2*(x*x + z*z),     2*(y*z + w*x), 0],
        [    2*(x*z + w*y),     2*(y*z - w*x), 1 - 2*(x*x + y*y), 0],
        [                0,                 0,                 0,   1],
    ], dtype=np.float32)

def arcball_project(mx, my, cx, cy, radius):
    """Project a screen point onto a virtual trackball sphere.
    Returns a unit 3D vector on the sphere surface."""
    x = (mx - cx) / radius
    y = (cy - my) / radius  # flip Y: screen Y is down, GL Y is up
    dist_sq = x*x + y*y
    if dist_sq <= 1.0:
        z = math.sqrt(1.0 - dist_sq)
    else:
        # Outside the sphere — project onto the hyperbolic sheet
        norm = math.sqrt(dist_sq)
        x /= norm
        y /= norm
        z = 0.0
    return np.array([x, y, z])

def quat_from_two_vectors(v0, v1):
    """Compute the rotation quaternion that rotates v0 to v1.
    Both must be unit vectors."""
    cross = np.cross(v0, v1)
    dot = np.dot(v0, v1)
    # Use half-angle formula for numerical stability
    w = 1.0 + dot
    if w < 1e-8:
        # Vectors are nearly anti-parallel
        # Pick an arbitrary perpendicular axis
        if abs(v0[0]) < 0.9:
            perp = np.cross(v0, np.array([1, 0, 0]))
        else:
            perp = np.cross(v0, np.array([0, 1, 0]))
        perp = perp / np.linalg.norm(perp)
        return np.array([0.0, perp[0], perp[1], perp[2]])
    q = np.array([w, cross[0], cross[1], cross[2]])
    return quat_normalize(q)


# Main Class

class RubiksCube3D:
    def __init__(self):
        pygame.init()
        self.width, self.height = 800, 600
        pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Rubik's Cube 3D")

        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

        # lighting 
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, (-2, 4, 5, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
        glMaterialfv(GL_FRONT, GL_SPECULAR, (1, 1, 1, 1))
        glMaterialf(GL_FRONT, GL_SHININESS, 50)

        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.width / self.height, 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0, 0, -8)

        # cube state 
        self.core = RubiksCubeCore()
        self.scrambler = CubeScrambler()
        self.solver = CubeSolver(self.core)

        # Trackball orientation quaternion [w, x, y, z]
        # Start with a pleasant viewing angle (~30° around X, ~-45° around Y)
        qx = np.array([math.cos(math.radians(-15)),
                        math.sin(math.radians(-15)), 0, 0])
        qy = np.array([math.cos(math.radians(22.5)),
                        0, math.sin(math.radians(22.5)), 0])
        self.orientation = quat_normalize(quat_multiply(qx, qy))
        self.trackball_radius = min(self.width, self.height) * 0.45

        # animation queue (for scripted moves, scramble, etc.)
        self.animating = False
        self.anim_q = []
        self.anim_frame = 0
        self.anim_speed = 5   # degrees per frame
        self.anim_current = None

        # snap animation (after slice drag release) 
        self.snap_animating = False
        self.snap_axis = None
        self.snap_layer = None
        self.snap_start_angle = 0.0
        self.snap_target_angle = 0.0
        self.snap_speed = 8.0  # degrees per frame for snap

        # input state 
        self.drag_global = False
        self.drag_slice = False
        self.drag_start = None           # (mx, my) at mouse-down
        self.drag_prev = None            # previous mouse pos for trackball

        # Slice drag state
        self.hit_pos = None              # (x,y,z) cubie grid position
        self.hit_normal = None           # (nx,ny,nz) face normal
        self.slice_axis_locked = False   # True once we've determined the rotation axis
        self.slice_rot_axis = None       # 'x', 'y', or 'z'
        self.slice_rot_layer = None      # -1, 0, or 1
        self.slice_rot_sign = 1          # +1 or -1 for direction mapping
        self.slice_screen_dir = None     # unit 2D vector on screen for angle projection
        self.current_slice_angle = 0.0   # live angle in degrees

        # cubelet dimensions
        self.size = 0.45
        self.gap = 0.06
        self.stride = self.size * 2 + self.gap

        self.colors = {
            'U': (1.0, 1.0, 1.0),    # white
            'D': (1.0, 1.0, 0.0),    # yellow
            'F': (0.0, 0.0, 1.0),    # blue
            'B': (0.0, 0.8, 0.0),    # green
            'R': (0.9, 0.0, 0.0),    # red
            'L': (1.0, 0.5, 0.0),    # orange
        }

        # Pre-build box face data (computed once, used every frame)
        self._box_faces = self._build_box_faces(self.size)

    # Geometry 

    @staticmethod
    def _build_box_faces(s):
        """Build the 6 faces of a cube centered at origin with half-size s.
        Each face has vertices in CCW winding order when viewed from outside
        (right-hand rule: thumb along normal, fingers curl in vertex order)."""
        return [
            # +X face  (normal = +X, look from +X toward origin)
            ((1, 0, 0), [
                (s, -s,  s),
                (s,  s,  s),
                (s,  s, -s),
                (s, -s, -s),
            ]),
            # -X face  (normal = -X, look from -X toward origin)
            ((-1, 0, 0), [
                (-s, -s, -s),
                (-s,  s, -s),
                (-s,  s,  s),
                (-s, -s,  s),
            ]),
            # +Y face  (normal = +Y, look from above)
            ((0, 1, 0), [
                (-s, s,  s),
                ( s, s,  s),
                ( s, s, -s),
                (-s, s, -s),
            ]),
            # -Y face  (normal = -Y, look from below)
            ((0, -1, 0), [
                (-s, -s, -s),
                ( s, -s, -s),
                ( s, -s,  s),
                (-s, -s,  s),
            ]),
            # +Z face  (normal = +Z, look from front)
            ((0, 0, 1), [
                (-s, -s, s),
                ( s, -s, s),
                ( s,  s, s),
                (-s,  s, s),
            ]),
            # -Z face  (normal = -Z, look from back)
            ((0, 0, -1), [
                ( s, -s, -s),
                (-s, -s, -s),
                (-s,  s, -s),
                ( s,  s, -s),
            ]),
        ]

    def draw_box(self):
        """Draw the black plastic cube body using pre-built face data."""
        glBegin(GL_QUADS)
        for (nx, ny, nz), verts in self._box_faces:
            glNormal3f(nx, ny, nz)
            for v in verts:
                glVertex3f(*v)
        glEnd()

    def draw_sticker(self, nx, ny, nz, color):
        """Draw a single colored sticker on the face defined by normal (nx,ny,nz).
        Uses explicit per-face vertex quads with a small epsilon offset to prevent z-fighting."""
        ss = self.size * 0.82   # sticker is slightly smaller than the face
        eps = 0.002             # z-fighting prevention offset

        glColor3fv(color)
        glBegin(GL_QUADS)
        glNormal3f(nx, ny, nz)

        if nx == 1:
            d = self.size + eps
            glVertex3f(d, -ss,  ss)
            glVertex3f(d,  ss,  ss)
            glVertex3f(d,  ss, -ss)
            glVertex3f(d, -ss, -ss)
        elif nx == -1:
            d = -(self.size + eps)
            glVertex3f(d, -ss, -ss)
            glVertex3f(d,  ss, -ss)
            glVertex3f(d,  ss,  ss)
            glVertex3f(d, -ss,  ss)
        elif ny == 1:
            d = self.size + eps
            glVertex3f(-ss, d,  ss)
            glVertex3f( ss, d,  ss)
            glVertex3f( ss, d, -ss)
            glVertex3f(-ss, d, -ss)
        elif ny == -1:
            d = -(self.size + eps)
            glVertex3f(-ss, d, -ss)
            glVertex3f( ss, d, -ss)
            glVertex3f( ss, d,  ss)
            glVertex3f(-ss, d,  ss)
        elif nz == 1:
            d = self.size + eps
            glVertex3f(-ss, -ss, d)
            glVertex3f( ss, -ss, d)
            glVertex3f( ss,  ss, d)
            glVertex3f(-ss,  ss, d)
        elif nz == -1:
            d = -(self.size + eps)
            glVertex3f( ss, -ss, d)
            glVertex3f(-ss, -ss, d)
            glVertex3f(-ss,  ss, d)
            glVertex3f( ss,  ss, d)

        glEnd()

    def draw_cubie(self, cubie):
        """Draw a single cubie: black plastic base + colored stickers."""
        glColor3f(0.12, 0.12, 0.12)
        self.draw_box()

        for (nx, ny, nz), col in cubie.stickers.items():
            self.draw_sticker(nx, ny, nz, self.colors[col])

    # ModelView helpers

    def _get_rotation_matrix(self):
        """Get the current 4x4 rotation matrix from the orientation quaternion."""
        return quat_to_matrix(self.orientation)

    def _build_modelview(self):
        """Push a fresh modelview matrix matching the current camera.
        Returns (model, proj, viewport) for picking/projection."""
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(0, 0, -8)
        rot = self._get_rotation_matrix()
        glMultMatrixf(rot.T.flatten())  # OpenGL expects column-major

        model = glGetDoublev(GL_MODELVIEW_MATRIX)
        proj = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)
        glPopMatrix()
        return model, proj, viewport

    # Ray-AABB Picking 

    def pick_cubelet(self, mx, my):
        """Cast a ray from screen coordinates (mx, my) and find the closest
        cubie hit. Returns (grid_pos, face_normal) or (None, None)."""
        model, proj, viewport = self._build_modelview()

        # Unproject near/far plane points to world space
        near = np.array(gluUnProject(mx, self.height - my, 0.0, model, proj, viewport))
        far  = np.array(gluUnProject(mx, self.height - my, 1.0, model, proj, viewport))
        ray_dir = far - near
        ray_dir = ray_dir / np.linalg.norm(ray_dir)
        ray_origin = near

        best_pos = None
        best_t = float('inf')
        best_normal = None

        for pos, cubie in self.core.get_cubies().items():
            x, y, z = pos
            center = np.array([x * self.stride, y * self.stride, z * self.stride])
            box_min = center - self.size
            box_max = center + self.size

            # Slab intersection
            tmin = -float('inf')
            tmax = float('inf')
            hit_axis = 0       # which axis set tmin
            hit_side = 0       # -1 = min slab, +1 = max slab

            miss = False
            for i in range(3):
                if abs(ray_dir[i]) < 1e-9:
                    # Ray is parallel to this slab
                    if ray_origin[i] < box_min[i] or ray_origin[i] > box_max[i]:
                        miss = True
                        break
                else:
                    inv_d = 1.0 / ray_dir[i]
                    t1 = (box_min[i] - ray_origin[i]) * inv_d
                    t2 = (box_max[i] - ray_origin[i]) * inv_d

                    # t1 should be the near slab, t2 the far
                    side = -1  # entering from the min side
                    if t1 > t2:
                        t1, t2 = t2, t1
                        side = 1  # entering from the max side

                    if t1 > tmin:
                        tmin = t1
                        hit_axis = i
                        hit_side = side

                    tmax = min(tmax, t2)

                    if tmin > tmax:
                        miss = True
                        break

            if miss:
                continue

            if tmax < 0:
                continue  # box is behind the camera

            if tmin < best_t:
                best_t = tmin
                best_pos = pos

                # Compute face normal from the entry slab
                normal = [0, 0, 0]
                normal[hit_axis] = hit_side
                best_normal = tuple(normal)

        return best_pos, best_normal

    # Slice Drag Logic 

    def _determine_slice_axis(self, dx, dy):
        """Once the mouse has moved enough, determine which rotation axis
        and direction mapping to use for this drag.

        Called once per drag, when the threshold is first exceeded.
        Uses the hit normal to find 2 candidate tangent axes, projects them
        to screen space, and picks the one most aligned with the drag."""
        nx, ny, nz = self.hit_normal
        x, y, z = self.hit_pos

        model, proj, viewport = self._build_modelview()

        # World-space center of the clicked cubie
        cx = x * self.stride
        cy = y * self.stride
        cz = z * self.stride

        # Determine the two tangent directions on this face
        # Each tangent crossed with the normal gives a rotation axis
        if abs(nx) > 0.5:
            tangents = [
                (np.array([0, 1, 0]), 'y_tangent'),
                (np.array([0, 0, 1]), 'z_tangent'),
            ]
        elif abs(ny) > 0.5:
            tangents = [
                (np.array([1, 0, 0]), 'x_tangent'),
                (np.array([0, 0, 1]), 'z_tangent'),
            ]
        else:  # abs(nz) > 0.5
            tangents = [
                (np.array([1, 0, 0]), 'x_tangent'),
                (np.array([0, 1, 0]), 'y_tangent'),
            ]

        normal = np.array([nx, ny, nz], dtype=float)
        drag_vec = np.array([dx, dy], dtype=float)
        drag_len = np.linalg.norm(drag_vec)
        if drag_len < 1e-6:
            return False
        drag_unit = drag_vec / drag_len

        best_score = -1
        best_rot_axis = None
        best_rot_layer = None
        best_screen_dir = None
        best_sign = 1

        for tangent, _label in tangents:
            # The rotation axis is cross(normal, tangent)
            rot_axis_3d = np.cross(normal, tangent)

            # Determine which primary axis this is
            abs_rot = np.abs(rot_axis_3d)
            primary = int(np.argmax(abs_rot))
            axis_name = ['x', 'y', 'z'][primary]

            # Which layer is being rotated
            layer = [x, y, z][primary]

            # Project tangent direction to screen space
            p1 = np.array(gluProject(cx, cy, cz, model, proj, viewport))
            p2 = np.array(gluProject(
                cx + tangent[0], cy + tangent[1], cz + tangent[2],
                model, proj, viewport))

            screen_tangent = np.array([p2[0] - p1[0], -(p2[1] - p1[1])])
            st_len = np.linalg.norm(screen_tangent)
            if st_len < 1e-6:
                continue
            screen_tangent /= st_len

            # How well does this screen tangent align with the drag?
            dot = np.dot(drag_unit, screen_tangent)
            if abs(dot) > best_score:
                best_score = abs(dot)
                best_rot_axis = axis_name
                best_rot_layer = layer
                best_screen_dir = screen_tangent

                # Sign: map the 3D rotation axis to the screen tangent.
                # Only use the cross product component sign — the projected
                # mouse delta in _update_slice_angle already carries the
                # positive/negative drag direction naturally.
                rot_component = rot_axis_3d[primary]
                best_sign = int(np.sign(rot_component)) if rot_component != 0 else 1

        if best_rot_axis is None:
            return False

        self.slice_rot_axis = best_rot_axis
        self.slice_rot_layer = best_rot_layer
        self.slice_screen_dir = best_screen_dir
        self.slice_rot_sign = best_sign
        self.slice_axis_locked = True
        return True

    def _update_slice_angle(self, mx, my):
        """Update current_slice_angle based on how far the mouse has moved
        from the drag start, projected onto the locked screen direction."""
        dx = mx - self.drag_start[0]
        dy = my - self.drag_start[1]
        drag_vec = np.array([dx, dy], dtype=float)

        # Project mouse displacement onto the screen-space tangent direction
        projected = np.dot(drag_vec, self.slice_screen_dir)

        # Scale: 100 pixels ≈ 90 degrees
        self.current_slice_angle = projected * (90.0 / 100.0) * self.slice_rot_sign

    def _snap_slice(self):
        """Called on mouse-up. Determine the snap target, commit state, and
        start the snap animation."""
        angle = self.current_slice_angle

        # Round to nearest 90°
        snapped = round(angle / 90.0) * 90.0
        # Number of 90° increments (can be negative)
        num_turns = int(round(angle / 90.0))

        if num_turns != 0:
            # Determine direction for core.rotate_layer
            # direction = +1 or -1 per call, repeated abs(num_turns) times
            direction = 1 if num_turns > 0 else -1
            for _ in range(abs(num_turns)):
                self.core.rotate_layer(self.slice_rot_axis,
                                       self.slice_rot_layer,
                                       direction)

        # Now animate from current visual angle to 0
        # (the core has already been updated, so the visual target is 0)
        remainder = self.current_slice_angle - snapped
        if abs(remainder) > 0.5:
            # Animate the remainder to 0
            self.snap_animating = True
            self.snap_axis = self.slice_rot_axis
            self.snap_layer = self.slice_rot_layer
            self.snap_start_angle = remainder
            self.snap_target_angle = 0.0
        else:
            self.snap_animating = False

        # Reset slice drag state
        self.current_slice_angle = remainder if self.snap_animating else 0.0
        self.drag_slice = False
        self.slice_axis_locked = False

    # Animation 

    def next_anim(self):
        """Pop the next queued animation (for scripted moves)."""
        if not self.anim_q:
            self.animating = False
            return
        self.anim_current = self.anim_q.pop(0)
        self.anim_frame = 0
        self.animating = True

    def update_anim(self):
        """Advance the current queued animation."""
        if not self.animating:
            self.next_anim()
            return

        axis, layer, direction = self.anim_current
        self.anim_frame += self.anim_speed
        if self.anim_frame >= 90:
            self.core.rotate_layer(axis, layer, direction)
            self.animating = False

    def update_snap_anim(self):
        """Advance the snap animation (smooth angular interpolation to 0)."""
        if not self.snap_animating:
            return

        # Move current_slice_angle toward 0
        if self.current_slice_angle > 0:
            self.current_slice_angle = max(0, self.current_slice_angle - self.snap_speed)
        else:
            self.current_slice_angle = min(0, self.current_slice_angle + self.snap_speed)

        if abs(self.current_slice_angle) < 0.5:
            self.current_slice_angle = 0.0
            self.snap_animating = False

    # Rendering 

    def draw_cube(self):
        """Render the full cube."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()

        # Apply trackball rotation
        rot = self._get_rotation_matrix()
        glMultMatrixf(rot.T.flatten())

        # Determine which slice is being animated (queued anim or live drag or snap)
        anim_axis = anim_layer = anim_dir = None
        anim_angle = 0

        if self.animating and self.anim_current:
            anim_axis, anim_layer, anim_dir = self.anim_current
            anim_angle = self.anim_frame * anim_dir

        # For slice drag or snap, we use current_slice_angle
        drag_axis = drag_layer = None
        drag_angle = 0
        if self.drag_slice and self.slice_axis_locked:
            drag_axis = self.slice_rot_axis
            drag_layer = self.slice_rot_layer
            drag_angle = self.current_slice_angle
        elif self.snap_animating:
            drag_axis = self.snap_axis
            drag_layer = self.snap_layer
            drag_angle = self.current_slice_angle

        for pos, cubie in self.core.get_cubies().items():
            x, y, z = pos
            tx = x * self.stride
            ty = y * self.stride
            tz = z * self.stride

            glPushMatrix()

            # Apply slice rotations BEFORE translation so cubelets
            # orbit the cube's origin as a group, not their own centers.

            # Queued animation rotation
            if anim_axis is not None:
                in_slice = False
                if anim_axis == 'x' and x == anim_layer: in_slice = True
                if anim_axis == 'y' and y == anim_layer: in_slice = True
                if anim_axis == 'z' and z == anim_layer: in_slice = True
                if in_slice:
                    if anim_axis == 'x': glRotatef(anim_angle, 1, 0, 0)
                    elif anim_axis == 'y': glRotatef(anim_angle, 0, 1, 0)
                    elif anim_axis == 'z': glRotatef(anim_angle, 0, 0, 1)

            # Live drag / snap animation rotation
            if drag_axis is not None and drag_angle != 0:
                in_slice = False
                if drag_axis == 'x' and x == drag_layer: in_slice = True
                if drag_axis == 'y' and y == drag_layer: in_slice = True
                if drag_axis == 'z' and z == drag_layer: in_slice = True
                if in_slice:
                    if drag_axis == 'x': glRotatef(drag_angle, 1, 0, 0)
                    elif drag_axis == 'y': glRotatef(drag_angle, 0, 1, 0)
                    elif drag_axis == 'z': glRotatef(drag_angle, 0, 0, 1)

            # Now translate the cubie out to its grid position
            glTranslatef(tx, ty, tz)

            self.draw_cubie(cubie)
            glPopMatrix()

        glPopMatrix()
        pygame.display.flip()

    # Input Handling 

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == QUIT:
                return False
            if e.type == KEYDOWN and e.key == K_ESCAPE:
                return False

            # Scramble (SPACE) / Solve (ENTER) 
            if e.type == KEYDOWN and not (self.animating or self.snap_animating
                                          or self.drag_slice):
                if e.key == K_SPACE:
                    moves = self.scrambler.scramble()
                    self.anim_q.extend(moves)
                    if not self.animating:
                        self.next_anim()
                elif e.key == K_RETURN:
                    moves = self.solver.solve()
                    if moves:
                        self.anim_q.extend(moves)
                        if not self.animating:
                            self.next_anim()

            if e.type == MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                self.drag_start = (mx, my)
                self.drag_prev = (mx, my)

                # Don't start new interactions during animations
                if self.animating or self.snap_animating:
                    continue

                hit, normal = self.pick_cubelet(mx, my)
                if hit is not None and normal is not None:
                    self.drag_slice = True
                    self.hit_pos = hit
                    self.hit_normal = normal
                    self.slice_axis_locked = False
                    self.current_slice_angle = 0.0
                else:
                    self.drag_global = True

            elif e.type == MOUSEMOTION:
                mx, my = e.pos

                if self.drag_global:
                    # Arcball / trackball rotation
                    prev_x, prev_y = self.drag_prev
                    cx, cy = self.width / 2, self.height / 2

                    v0 = arcball_project(prev_x, prev_y, cx, cy, self.trackball_radius)
                    v1 = arcball_project(mx, my, cx, cy, self.trackball_radius)

                    q_delta = quat_from_two_vectors(v0, v1)
                    self.orientation = quat_normalize(
                        quat_multiply(q_delta, self.orientation))

                    self.drag_prev = (mx, my)

                elif self.drag_slice:
                    if not self.slice_axis_locked:
                        # Check if we've moved enough to determine the axis
                        dx = mx - self.drag_start[0]
                        dy = my - self.drag_start[1]
                        if dx * dx + dy * dy >= 64:  # 8px threshold
                            # Determine axis using full delta from original start
                            # (incorporates the initial 8 pixels — no jump)
                            self._determine_slice_axis(dx, dy)

                    if self.slice_axis_locked:
                        self._update_slice_angle(mx, my)

            elif e.type == MOUSEBUTTONUP and e.button == 1:
                if self.drag_slice and self.slice_axis_locked:
                    self._snap_slice()
                elif self.drag_slice:
                    # User clicked a cubie but didn't drag enough to lock an axis
                    self.drag_slice = False

                self.drag_global = False
                self.drag_prev = None

        return True

    # Main Loop 

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            running = self.handle_events()
            self.update_anim()
            self.update_snap_anim()
            self.draw_cube()
            clock.tick(60)

        pygame.quit()
