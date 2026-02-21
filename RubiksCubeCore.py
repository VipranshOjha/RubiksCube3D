# RubiksCubeCore.py
# Pure cube logic - no pygame, no OpenGL

from dataclasses import dataclass
import copy

@dataclass
class Cubie:
    pos: tuple     # (x,y,z)
    stickers: dict # {(nx,ny,nz): 'U'/'D'/'F'/'B'/'R'/'L'}

class RubiksCubeCore:
    def __init__(self):
        self.reset()

    def reset(self):
        self.cubies = {}
        colors = {
            (0, 1, 0): 'U',
            (0, -1, 0): 'D',
            (0, 0, 1): 'F',
            (0, 0, -1): 'B',
            (1, 0, 0): 'R',
            (-1, 0, 0): 'L'
        }
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                for z in (-1, 0, 1):
                    if (x,y,z) == (0,0,0): continue
                    stickers = {}
                    for normal,color in colors.items():
                        nx,ny,nz = normal
                        if (nx!=0 and x==nx) or (ny!=0 and y==ny) or (nz!=0 and z==nz):
                            stickers[normal] = color
                    self.cubies[(x,y,z)] = Cubie((x,y,z), stickers)

    # --- rotation engine ---
    def rotate_layer(self, axis, layer, direction):
        new = {}
        for pos,cubie in self.cubies.items():
            x,y,z = cubie.pos
            rotated = False

            if axis == 'x' and x == layer:
                rotated = True
                new_pos = (x, -z*direction, y*direction)
            elif axis == 'y' and y == layer:
                rotated = True
                new_pos = (z*direction, y, -x*direction)
            elif axis == 'z' and z == layer:
                rotated = True
                new_pos = (-y*direction, x*direction, z)
            else:
                new[pos] = copy.deepcopy(cubie)
                continue

            new_stickers = {}
            for (nx,ny,nz),col in cubie.stickers.items():
                if axis == 'x':
                    nn = (nx, -nz*direction, ny*direction)
                elif axis == 'y':
                    nn = (nz*direction, ny, -nx*direction)
                elif axis == 'z':
                    nn = (-ny*direction, nx*direction, nz)
                new_stickers[nn] = col

            new[new_pos] = Cubie(new_pos, new_stickers)

        self.cubies = new

    def get_cubies(self):
        return self.cubies
