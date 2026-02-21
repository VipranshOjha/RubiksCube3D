# 3D Rubik's Cube Simulator & Optimal Solver

A fully interactive, mathematically robust 3D Rubik's Cube simulator built from scratch using Python, Pygame, and PyOpenGL. This project features intuitive mouse-driven interactions, smooth animations, and an integrated optimal solver powered by the Kociemba Two-Phase Algorithm.

## ✨ Features

* **Advanced 3D Rendering:** Built with PyOpenGL featuring dynamic lighting, depth testing, and strict anti-z-fighting geometry.
* **Gimbal-Lock-Free Camera:** Uses Quaternion-based arcball/trackball mathematics allowing you to rotate the entire cube globally without axis flipping or inverted controls.
* **Dynamic Slice Dragging:** Features robust Ray-AABB intersection (raycasting). You can click any individual sticker and drag your mouse to seamlessly rotate that specific row or column. Releasing the mouse smoothly snaps the layer to the nearest 90-degree increment.
* **Optimal Kociemba Solver:** Integrated with the `rubik-twophase` engine to calculate the absolute optimal solution (20 moves or fewer) for any scrambled state in milliseconds.
* **Animated Automation:** Watch the cube automatically scramble and solve itself with smooth, queue-based rendering animations.

## 🎮 Controls

* **Left Click + Drag (on background):** Rotate the entire cube globally.
* **Left Click + Drag (on a cubie):** Dynamically rotate that specific slice/layer in the direction of your mouse drag.
* **`SPACE`:** Automatically scramble the cube (20 random moves).
* **`ENTER` / `RETURN`:** Calculate the optimal solution and watch the cube solve itself.
* **`R`:** Instantly reset the cube to the solved state.
* **`ESC`:** Exit the simulator.

## 🛠️ Installation & Setup

**Prerequisites:** Python 3.x

### 1. **Clone the repository:**
```
   git clone [https://github.com/VipranshOjha/RubiksCube3D.git](https://github.com/VipranshOjha/RubiksCube3D.git)
   cd RubiksCube3D
```
### 2. Install the dependencies:
```
pip install pygame PyOpenGL PyOpenGL_accelerate numpy rubik-twophase
```
### 3. ⚠️ Important: First-Run Initialization (Pruning Tables)
Because this project uses a pure-Python implementation of the Kociemba algorithm, it must generate massive mathematical "pruning tables" on its very first run.

Run this command in your terminal before playing to generate the tables:
```
python -c "import twophase.solver as sv; print(sv.solve('DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD', 20, 5))"
```
Note: This process takes roughly 15-30 minutes depending on your CPU. It is a one-time operation. Once complete, the tables are cached to your hard drive, and the solver will run instantly from then on.

 ### 4. Run the Simulator:
```
python main.py
```

## 🏗️ Project Architecture
main.py: The entry point that initializes the window and runs the main loop.

RubiksCube3D.py: The core rendering engine. Handles PyOpenGL matrices, quaternion trackball math, raycasting for mouse interactions, and animation queues.

RubiksCubeCore.py: The logical backend. Manages the 3D grid coordinates, piece states, matrix rotations, and face/sticker data independently of the visual renderer.

Scrambler.py: Generates sequences of random moves to scramble the cube state.

Solver.py: Bridges the 3D spatial state with the Kociemba engine. Translates 3D normal vectors and coordinates into the 54-character string format required by the solver, and parses the output back into engine-readable moves.
