This project is a 2D Level Editor and Game Engine built using Python, designed to create and manage interactive game levels with advanced physics, rendering, and user interface capabilities. It provides a robust framework for game developers to design, edit, and simulate game environments efficiently.

Key Features:
Level Editor:

Fully functional level editor with tools for terrain editing, object placement, and path creation.
Supports various object types, including traps, liquids, platforms, and collectables, with customizable properties and behaviors.
Dynamic UI for selecting and configuring objects, tiles, and shaders.
Physics Simulation:

Integrated Pymunk physics engine for collision detection, rigid body dynamics, and simulation of physical interactions.
Customizable physical properties for objects, such as elasticity, friction, and mass.
Rendering and Shaders:

Utilizes Moderngl for GPU-accelerated rendering and shader effects.
Advanced visual effects, including lighting, liquid warping, and texture blending.
Dynamic shader data updates for real-time visual feedback.
File Management System:

Multi-threaded file loading and saving system to handle large game levels efficiently.
Implements coroutines and generators for asynchronous tasks, such as loading assets and updating progress bars in real-time.
Supports JSON-based file formats for terrain, objects, and settings.
UI System:

Built with Pygame GUI, featuring interactive menus for settings, level selection, and in-game controls.
Includes sliders, buttons, and dropdowns for user interaction, such as adjusting brightness, zoom, and volume.
Asset Management:

Modular system for loading and managing assets, including textures, animations, and object definitions.
Dynamic loading of shaders, terrain tiles, and object assets from external files.
Performance Optimization:

Optimized rendering by updating only on-screen objects and tiles.
Multi-threading for resource-intensive tasks like saving and loading levels.
Custom Collision System:

Custom collision types and masks for precise interaction between objects, terrain, and liquids.
Technologies Used:
Python: Core programming language.
Pygame: For rendering, input handling, and UI development.
Pymunk: For physics simulation and collision handling.
Moderngl: For GPU-accelerated shaders and advanced visual effects.
JSON: For saving and loading level data.
Use Case:
This project is ideal for game developers looking to create 2D games with complex physics, dynamic rendering, and a user-friendly level editor. It provides a complete pipeline for designing, testing, and exporting game levels.
