# 🧊 3D Rubik’s Cube Simulator & Optimal Solver

A fully interactive, mathematically robust 3D Rubik’s Cube simulator built from scratch using **Python, Pygame, and PyOpenGL**, featuring real-time mouse-driven manipulation and an integrated optimal solver powered by the Kociemba Two-Phase Algorithm.

> This project combines real-time 3D graphics, quaternion mathematics, computational geometry, and optimal search algorithms into one cohesive system.


---


## 🚀 Highlights


### 🧮 Quaternion-Based Trackball (No Gimbal Lock)

Uses true quaternion math for arcball-style rotation, ensuring:
- Smooth global cube rotation  

- No axis flipping  

- No gimbal lock artifacts  

- Natural camera behavior  


---


### 🎯 Accurate Raycasting (Ray–AABB Intersection)

Click any sticker and rotate that exact slice using:

- 3D ray casting from screen space  

- Slab-based Ray–AABB intersection  

- Face-normal detection  

- Screen-space projection mapping for drag direction  



This is mathematically precise geometric picking — not an approximation.


---


### 🔄 Dynamic Slice Dragging with Snap Logic

- Continuous real-time slice rotation  

- Projection-based angle detection  

- Automatic snapping to nearest 90°  

- Smooth visual correction animation  


---


### ⚡ Optimal Solver (≤ 20 Moves)

Integrated with the Kociemba Two-Phase Algorithm:

- Always finds a solution in **20 moves or fewer**  

- Pure-Python implementation via `rubik-twophase`  

- Converts 3D cube state → 54-character facelet string  

- Parses solver output back into engine moves  

- Fully animated playback  


---


## 🎮 Controls

| Action | Control |
|--------|---------|
| Rotate entire cube | **Left Click + Drag (background)** |
| Rotate slice | **Left Click + Drag (on cubie)** |
| Scramble (20 moves) | `SPACE` |
| Solve optimally | `ENTER` |
| Reset to solved | `R` |
| Exit | `ESC` |

---


## 🛠 Installation

### 1️⃣ Clone the repository

```

git clone https://github.com/VipranshOjha/RubiksCube3D.git

cd RubiksCube3D

```


### 2️⃣ Install dependencies

```

pip install -r requirements.txt

pip install rubik-twophase

```


### 3️⃣ First-Run Initialization (Important ⚠️)

On first run, the solver must generate large pruning tables.

Run once:

```

python -c "import twophase.solver as sv;

print(sv.solve('DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD', 20, 5))"

```

⏳ Takes ~15–30 minutes depending on CPU

💾 Cached permanently after generation

⚡ All future solves are near-instant


### 4️⃣ Run the simulator

```

python main.py

```

---


## 🧠 Architecture


The project is cleanly separated into rendering, logic, and algorithmic solving.


### 🖥 Rendering Engine

RubiksCube3D.py

- OpenGL lighting + depth testing

- Quaternion trackball math

- Ray–AABB picking

- Animation queues

- Snap interpolation

- Matrix-based slice rotations
  

---


### 🧩 Cube Logic Core

RubiksCubeCore.py

- Pure state engine

- 3D coordinate system (-1, 0, 1 grid)

- Sticker normal tracking

- Layer rotation transformations

- Deep-copy safe state mutation

- Completely independent of rendering.


---
  

### 🎲 Scrambler

Scrambler.py

- Generates Kociemba-compatible scramble sequences

- Avoids redundant axis-layer repetitions


---


### 🤖 Solver Bridge

Solver.py

- Builds 54-character face string in correct facelet order

- Dynamically maps center colors

- Parses numeric solver notation (R1, R2, R3)

- Converts solution into engine-compatible move tuples

- Validates solved state


---


## 🔬 Technical Concepts Demonstrated

- Quaternion algebra

- 4×4 transformation matrices

- OpenGL rendering pipeline

- Ray casting & slab intersection

- Projection math (gluProject / gluUnProject)

- Discrete 3D rotational transformations

- Optimal search (two-phase solving algorithm)

- State → string → state algorithm bridging


---


## 📁 Project Structure

```

RubiksCube3D/

│

├── main.py

├── RubiksCube3D.py      # Rendering + input engine

├── RubiksCubeCore.py    # Cube state logic

├── Scrambler.py

├── Solver.py

└── requirements.txt

```

---


## 📜 License

MIT License
