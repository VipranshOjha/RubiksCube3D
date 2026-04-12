# TrainingSolver.py
from RubiksCubeCore import RubiksCubeCore

class TrainingSolver:
    def __init__(self, core: RubiksCubeCore):
        self.core = core

    def get_step_info(self):
        """
        Determines the current step of the Beginner's Method and returns
        instructions, the target pieces, and suggested moves.
        """
        if self.is_solved():
            return "Solved!", [], []

        # 1. White Cross
        if not self.is_white_cross_solved():
            return self.get_white_cross_step()

        # 2. First Layer (White Corners)
        if not self.is_first_layer_solved():
            return self.get_first_layer_step()

        # 3. Second Layer (Middle Edges)
        if not self.is_second_layer_solved():
            return self.get_second_layer_step()

        # 4. Yellow Cross
        if not self.is_yellow_cross_solved():
            return self.get_yellow_cross_step()

        # 5. Yellow Edges (Permute)
        if not self.is_yellow_edges_solved():
            return self.get_yellow_edges_step()

        # 6. Yellow Corners (Position)
        if not self.is_yellow_corners_positioned():
            return self.get_yellow_corners_position_step()

        # 7. Yellow Corners (Orient)
        return self.get_yellow_corners_orient_step()

    def is_solved(self):
        """Check if the cube is solved by verifying each face's uniform color."""
        cubies = self.core.get_cubies()
        face_normals = [(0,1,0), (0,-1,0), (0,0,1), (0,0,-1), (1,0,0), (-1,0,0)]
        for normal in face_normals:
            color = None
            # Check all cubies on this face
            for pos, cubie in cubies.items():
                if normal in cubie.stickers:
                    if color is None:
                        color = cubie.stickers[normal]
                    elif cubie.stickers[normal] != color:
                        return False
        return True

    def get_center_color(self, normal):
        return self.core.get_cubies().get(normal).stickers.get(normal)

    def is_white_cross_solved(self):
        cubies = self.core.get_cubies()
        white_center = self.get_center_color((0, 1, 0)) # U is white
        # Check 4 edges: (0,1,1), (0,1,-1), (1,1,0), (-1,1,0)
        edges = [(0,1,1), (0,1,-1), (1,1,0), (-1,1,0)]
        for pos in edges:
            if cubies[pos].stickers.get((0,1,0)) != white_center:
                return False
            # Also check side alignment
            for normal, color in cubies[pos].stickers.items():
                if normal != (0,1,0):
                    if color != self.get_center_color(normal):
                        return False
        return True

    def get_white_cross_step(self):
        # Find a white edge not in place
        cubies = self.core.get_cubies()
        white_center = self.get_center_color((0, 1, 0))

        # Target edges for the cross
        cross_positions = [(0,1,1), (0,1,-1), (1,1,0), (-1,1,0)]

        # Simple heuristic: find any white edge piece
        for pos, cubie in cubies.items():
            if white_center in cubie.stickers.values() and len(cubie.stickers) == 2:
                # If not in one of the cross positions or not correctly oriented
                if pos not in cross_positions or cubie.stickers.get((0,1,0)) != white_center:
                    # Suggest a move to bring it closer (very simplified)
                    # For a real training mode, we'd have a full BFS or lookup table
                    # Here we just suggest the first move of a known sequence if applicable
                    return "Step 1: Form the White Cross on the top layer. Align edge colors with side centers.", [pos], ["F", "R", "U", "L", "B"]

        return "Step 1: Form the White Cross on the top layer. Align edge colors with side centers.", cross_positions, []

    def is_first_layer_solved(self):
        if not self.is_white_cross_solved(): return False
        cubies = self.core.get_cubies()
        white_center = self.get_center_color((0, 1, 0))
        corners = [(1,1,1), (1,1,-1), (-1,1,1), (-1,1,-1)]
        for pos in corners:
            if cubies[pos].stickers.get((0,1,0)) != white_center:
                return False
            for normal, color in cubies[pos].stickers.items():
                if normal[1] == 0: # side faces
                    if color != self.get_center_color(normal):
                        return False
        return True

    def get_first_layer_step(self):
        return "Step 2: Solve the White Corners to complete the first layer.", [(1,1,1), (1,1,-1), (-1,1,1), (-1,1,-1)], []

    def is_second_layer_solved(self):
        if not self.is_first_layer_solved(): return False
        cubies = self.core.get_cubies()
        middle_edges = [(1,0,1), (1,0,-1), (-1,0,1), (-1,0,-1)]
        for pos in middle_edges:
            for normal, color in cubies[pos].stickers.items():
                if color != self.get_center_color(normal):
                    return False
        return True

    def get_second_layer_step(self):
        return "Step 3: Solve the middle layer edges.", [(1,0,1), (1,0,-1), (-1,0,1), (-1,0,-1)], ["U R U' R' U' F' U F", "U' L' U L U F U' F'"]

    def is_yellow_cross_solved(self):
        if not self.is_second_layer_solved(): return False
        cubies = self.core.get_cubies()
        yellow_center = self.get_center_color((0, -1, 0)) # D is yellow
        edges = [(0,-1,1), (0,-1,-1), (1,-1,0), (-1,-1,0)]
        for pos in edges:
            if cubies[pos].stickers.get((0,-1,0)) != yellow_center:
                return False
        return True

    def get_yellow_cross_step(self):
        return "Step 4: Form a Yellow Cross on the bottom face.", [(0,-1,1), (0,-1,-1), (1,-1,0), (-1,-1,0)], ["F R U R' U' F'"]

    def is_yellow_edges_solved(self):
        if not self.is_yellow_cross_solved(): return False
        cubies = self.core.get_cubies()
        edges = [(0,-1,1), (0,-1,-1), (1,-1,0), (-1,-1,0)]
        for pos in edges:
            for normal, color in cubies[pos].stickers.items():
                if normal[1] != 0: continue
                if color != self.get_center_color(normal):
                    return False
        return True

    def get_yellow_edges_step(self):
        return "Step 5: Align Yellow Cross edges with side centers.", [(0,-1,1), (0,-1,-1), (1,-1,0), (-1,-1,0)], ["R U R' U R U2 R'"]

    def is_yellow_corners_positioned(self):
        if not self.is_yellow_edges_solved(): return False
        cubies = self.core.get_cubies()
        corners = [(1,-1,1), (1,-1,-1), (-1,-1,1), (-1,-1,-1)]
        for pos in corners:
            # Check if corner has the right 3 colors
            required_colors = {self.get_center_color((0,-1,0))}
            for i in range(3):
                norm = [0,0,0]
                norm[i] = pos[i]
                if norm[i] != 0:
                    required_colors.add(self.get_center_color(tuple(norm)))

            actual_colors = set(cubies[pos].stickers.values())
            if required_colors != actual_colors:
                return False
        return True

    def get_yellow_corners_position_step(self):
        return "Step 6: Move Yellow Corners to their correct positions.", [(1,-1,1), (1,-1,-1), (-1,-1,1), (-1,-1,-1)], ["U R U' L' U R' U' L"]

    def get_yellow_corners_orient_step(self):
        return "Step 7: Orient Yellow Corners to complete the cube.", [(1,-1,1), (1,-1,-1), (-1,-1,1), (-1,-1,-1)], ["R' D' R D"]
