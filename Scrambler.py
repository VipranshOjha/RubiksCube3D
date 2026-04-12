# Scrambler.py

import random


class CubeScrambler:
    def __init__(self):
        self.axes = ['x', 'y', 'z']
        self.layers = [-1, 1]           # outer layers only (kociemba-compatible)
        self.directions = [-1, 1]

    def scramble(self, num_moves=25):
        """Generate a random scramble sequence.

        Returns:
            list of (axis, layer, direction) tuples.
        """
        moves = []
        prev_axis = None
        prev_layer = None

        for _ in range(num_moves):
            # Avoid consecutive moves on the same axis+layer
            while True:
                axis = random.choice(self.axes)
                layer = random.choice(self.layers)
                if axis != prev_axis or layer != prev_layer:
                    break

            direction = random.choice(self.directions)
            moves.append((axis, layer, direction))
            prev_axis = axis
            prev_layer = layer

        return moves
