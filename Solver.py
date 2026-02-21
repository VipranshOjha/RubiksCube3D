# Solver.py
# Optimal Rubik's Cube solver using the Kociemba two-phase algorithm.
# Pure logic — no Pygame, no OpenGL.
# Returns a list of (axis, layer, direction) tuples for the animation queue.

import twophase.solver as sv
from RubiksCubeCore import RubiksCubeCore


class CubeSolver:
    def __init__(self, core):
        """
        Args:
            core: A RubiksCubeCore instance whose state we inspect and solve.
        """
        self.core = core
        self.move_history = []

        # ------------------------------------------------------------------ #
        #  Facelet reading order for the kociemba cube string                  #
        #                                                                      #
        #  kociemba expects a 54-char string: U1..U9 R1..R9 F1..F9            #
        #                                    D1..D9 L1..L9 B1..B9            #
        #  Each group of 9 is top-left → bottom-right when looking at         #
        #  that face head-on (with U on top for equator faces).               #
        #                                                                      #
        #  Each entry is ( (x,y,z) position , (nx,ny,nz) sticker normal ).    #
        # ------------------------------------------------------------------ #

        U = (0, 1, 0)
        D = (0, -1, 0)
        F = (0, 0, 1)
        B = (0, 0, -1)
        R = (1, 0, 0)
        L = (-1, 0, 0)

        self._face_order = [
            # ---- U face (y=1, looking down; top row is toward B) ----
            ((-1,1,-1),U), ((0,1,-1),U), ((1,1,-1),U),
            ((-1,1, 0),U), ((0,1, 0),U), ((1,1, 0),U),
            ((-1,1, 1),U), ((0,1, 1),U), ((1,1, 1),U),

            # ---- R face (x=1, looking from +X; left col is F side) ----
            ((1,1, 1),R), ((1,1, 0),R), ((1,1,-1),R),
            ((1,0, 1),R), ((1,0, 0),R), ((1,0,-1),R),
            ((1,-1,1),R), ((1,-1,0),R), ((1,-1,-1),R),

            # ---- F face (z=1, looking from +Z; left col is L side) ----
            ((-1,1,1),F), ((0,1,1),F), ((1,1,1),F),
            ((-1,0,1),F), ((0,0,1),F), ((1,0,1),F),
            ((-1,-1,1),F),((0,-1,1),F),((1,-1,1),F),

            # ---- D face (y=-1, looking from -Y; top row is toward F) ----
            ((-1,-1,1),D),  ((0,-1,1),D),  ((1,-1,1),D),
            ((-1,-1,0),D),  ((0,-1,0),D),  ((1,-1,0),D),
            ((-1,-1,-1),D), ((0,-1,-1),D), ((1,-1,-1),D),

            # ---- L face (x=-1, looking from -X; left col is B side) ----
            ((-1,1,-1),L), ((-1,1, 0),L), ((-1,1, 1),L),
            ((-1,0,-1),L), ((-1,0, 0),L), ((-1,0, 1),L),
            ((-1,-1,-1),L),((-1,-1,0),L),((-1,-1,1),L),

            # ---- B face (z=-1, looking from -Z; left col is R side) ----
            ((1,1,-1),B),  ((0,1,-1),B),  ((-1,1,-1),B),
            ((1,0,-1),B),  ((0,0,-1),B),  ((-1,0,-1),B),
            ((1,-1,-1),B), ((0,-1,-1),B), ((-1,-1,-1),B),
        ]

        # ------------------------------------------------------------------ #
        #  Notation → engine move mapping                                      #
        #                                                                      #
        #  Verified against RubiksCubeCore.rotate_layer():                     #
        #    axis='y',layer=1,dir=+1  rotates UF→UR (= standard U CW)        #
        #    axis='x',layer=1,dir=-1  rotates UFR→UBR (= standard R CW)      #
        #    axis='z',layer=1,dir=-1  rotates UF→UR  (= standard F CW)       #
        # ------------------------------------------------------------------ #

        self._notation_map = {
            'U': ('y',  1, -1),   "U'": ('y',  1,  1),
            'D': ('y', -1,  1),   "D'": ('y', -1, -1),
            'R': ('x',  1, -1),   "R'": ('x',  1,  1),
            'L': ('x', -1,  1),   "L'": ('x', -1, -1),
            'F': ('z',  1, -1),   "F'": ('z',  1,  1),
            'B': ('z', -1,  1),   "B'": ('z', -1, -1),
        }

    # ------------------------------------------------------------------ #
    #  State inspection                                                    #
    # ------------------------------------------------------------------ #

    def is_solved(self):
        """Check if every outer face of the cube is a uniform color."""
        face_normals = [
            (0,1,0), (0,-1,0), (0,0,1), (0,0,-1), (1,0,0), (-1,0,0),
        ]
        face_colors = {n: set() for n in face_normals}

        for _pos, cubie in self.core.get_cubies().items():
            for normal, color_letter in cubie.stickers.items():
                if normal in face_colors:
                    face_colors[normal].add(color_letter)

        return all(len(c) == 1 for c in face_colors.values())

    # ------------------------------------------------------------------ #
    #  Kociemba cube-string builder                                        #
    # ------------------------------------------------------------------ #

    def _get_kociemba_string(self):
        """Read the current cube state and produce the 54-char kociemba string.

        Handles center-piece movements (from middle-layer rotations) by
        dynamically mapping each sticker color to the kociemba face label
        based on whichever color currently sits at each face's center.
        """
        cubies = self.core.get_cubies()

        # Determine center colors → kociemba face labels
        center_info = [
            ('U', (0,  1,  0), (0,  1,  0)),
            ('R', (1,  0,  0), (1,  0,  0)),
            ('F', (0,  0,  1), (0,  0,  1)),
            ('D', (0, -1,  0), (0, -1,  0)),
            ('L', (-1, 0,  0), (-1, 0,  0)),
            ('B', (0,  0, -1), (0,  0, -1)),
        ]
        color_to_face = {}
        for face_label, pos, normal in center_info:
            center_color = cubies[pos].stickers[normal]
            color_to_face[center_color] = face_label

        # Build the 54-char string
        result = []
        for pos, normal in self._face_order:
            color = cubies[pos].stickers[normal]
            result.append(color_to_face[color])

        return ''.join(result)

    # ------------------------------------------------------------------ #
    #  Solution parser                                                     #
    # ------------------------------------------------------------------ #

    def _parse_solution(self, solution_string):
        """Convert a RubikTwoPhase solution string into move tuples.

        RubikTwoPhase outputs numeric notation:
            R1 = R  (CW 90°),  R2 = R2 (180°),  R3 = R' (CCW 90°)
        with a trailing annotation like "(19f)" that must be stripped.
        """
        if not solution_string or solution_string.startswith('Error'):
            return []

        # Strip trailing move-count annotation like "(19f)"
        text = solution_string.strip()
        if '(' in text:
            text = text[:text.rfind('(')].strip()

        moves = []
        for token in text.split():
            if len(token) < 2:
                print(f"Warning: unrecognized move token '{token}'")
                continue

            face = token[0]         # e.g. 'R'
            suffix = token[1:]      # e.g. '1', '2', '3', or "'"

            if suffix == '1' or suffix == '':
                # CW 90° — use the base face key
                key = face
                count = 1
            elif suffix == '2':
                # 180° — two CW moves
                key = face
                count = 2
            elif suffix == '3' or suffix == "'":
                # CCW 90° — use the prime key
                key = face + "'"
                count = 1
            else:
                print(f"Warning: unrecognized move token '{token}'")
                continue

            if key in self._notation_map:
                move = self._notation_map[key]
                moves.extend([move] * count)
            else:
                print(f"Warning: unmapped move '{key}' from token '{token}'")

        return moves

    # ------------------------------------------------------------------ #
    #  Main solve method                                                   #
    # ------------------------------------------------------------------ #

    def solve(self):
        """Compute an optimal solution using the Kociemba two-phase algorithm.

        Returns:
            list of (axis, layer, direction) tuples, or empty list if
            already solved or on error.

        Note: The first call may take 15-30 seconds while the library
        generates its pruning tables (one-time cost, cached to disk).
        """
        if self.is_solved():
            print("Cube is already solved!")
            return []

        try:
            cube_string = self._get_kociemba_string()
            print(f"Cube state: {cube_string}")

            # max_length=20: find ≤20-move solution
            # timeout=5: spend up to 5 seconds searching
            solution = sv.solve(cube_string, 20, 5)
            print(f"Solution: {solution}")

            self.move_history = self._parse_solution(solution)
            return list(self.move_history)

        except Exception as e:
            print(f"Solver error: {e}")
            print("The cube may be in an unsolvable state.")
            return []

    # ------------------------------------------------------------------ #
    #  Utility                                                             #
    # ------------------------------------------------------------------ #

    def get_move_notation(self):
        """Return the solution as a human-readable move string."""
        reverse_map = {v: k for k, v in self._notation_map.items()}
        return " ".join(
            reverse_map.get(m, str(m)) for m in self.move_history
        )
