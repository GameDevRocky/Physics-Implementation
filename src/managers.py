import pygame
import pymunk
import os
import json
import threading
import time
import moderngl
import numpy
from objects import*
from particles import*
from Editor import Editor
from Input import InputHandler
from levels import Level
from Tile import Tile
from collections.abc import Iterable


class EditorManager:

    def __init__(self, app):
        from App import Application
        self.active = False

        self.app : Application = app
        self.input : InputHandler = app.input
        self.assets : AssetsManager = self.app.assets_manager
        self.current_level = None
        self.levels = {}
        self.editor = Editor(self)
        self.settings = {'game_transition_weight' : 1, 'fade_steps' : 100}
        self.generatorTasks = {}
        self.saving = False
    
    def initialize(self):
        self.generatorTasks['fade_out'] = self.fade_out()
        self.input.EditorAction.active = True
        self.editor.initialize(self.current_level)
        self.current_level.initialize()
    
    def create_new_level(self, data):
        level_name = data['name']

        if level_name == '':
            level_name =  f'Level{len(os.listdir("data/Levels")) + 1}'
        try:
            level_width = int(data['width'])
        except:
            level_width = 100
        try:
            level_height = int(data['height'])
        except:
            level_height = 100
        try:
            level_layers = int(data['layers'])
        except:
            level_layers = 3
        try:
            level_tileSize = int(data['tileSize'])
        except:
            level_tileSize = 20
        level_width = pygame.math.clamp(level_width, 50, 750)
        level_height = pygame.math.clamp(level_height, 50, 750)
        level_layers = pygame.math.clamp(level_layers, 1, 6)
        level_tileSize = pygame.math.clamp(level_tileSize, 15, 40)

        os.makedirs(f"data/Levels/{level_name}", exist_ok=True)
        data = {
            "cache" : {
            "width": level_width,
            "height": level_height,
            "tileSize": level_tileSize,
            'layers' : level_layers
        },
            "tiles" : {}
        }
        for x in range(data['cache']['width']):
            for y in range(data['cache']['height']):
                key = f"{x},{y}"
                data['tiles'][key] = {}
                for layer in range(data['cache']['layers']):
                    
                    data['tiles'][key][layer] = {
                        'coll': False,
                        'type': "empty",
                        'variation': [0, 0]  
                    }

        with open(f'data/Levels/{level_name}/terrain.json', 'w') as file:
            json.dump(data, file, indent=1)
        with open(f'data/Levels/{level_name}/objects.json', 'w') as file:
            json.dump({}, file, indent=1)
        with open(f'data/Levels/{level_name}/settings.json', 'w') as file:
            json.dump({'world_brightness' : 1, 'background': 1}, file)

    def load_level(self, level_path):
        if level_path in self.levels.keys():
            self.current_level = self.levels.get(level_path)
            self.initialize()
        else:
            level = Level(self)
            self.current_level = level
            thread = threading.Thread(target=lambda: self.run_loading_thread(level, level_path, lambda level = level: self.finished_loading_resources(level, level_path)))
            thread.start()
    
    def run_loading_thread(self, level : Level, level_path, callback):
        try:
            for percent in self.load_resources(level, level_path):
                level.loaded_percentage = percent * 100
            
        except StopIteration:
            if level.loaded_percentage != 100:
                level.loaded_percentage = 100
            level.saved_percentage = 100
        
        if callable(callback):
            callback()

    def load_resources(self, level : Level, filename):
        level.name = filename
        directory = 'data/Levels/'
        terrain_path = os.path.join(directory, filename, 'terrain.json')
        objects_path = os.path.join(directory, filename, 'objects.json')
        settings_path = os.path.join(directory, filename, 'settings.json')

        with open(terrain_path, 'r') as file:
            terrain_data = json.load(file)
        with open(objects_path, 'r') as file:
            objects_data = json.load(file)
        with open(settings_path, 'r') as file:
            settings_data = json.load(file)

        level.world_width = terrain_data['cache']['width']
        level.world_height = terrain_data['cache']['height']
        level.tile_size = terrain_data['cache']['tileSize']
        level.layers = terrain_data['cache']['layers']
        level.bounding_rect = pygame.Rect(0,0, level.world_width * level.tile_size, level.world_height * level.tile_size)
        level.spaces = [pymunk.Space() for _ in range(level.layers)]
        level.add_collision_handlers()

        terrain_size = level.world_width * level.world_height * level.layers
        objects_size = len(objects_data)
        settings_size = len(settings_data)
        total_file_size = terrain_size * 2 + objects_size + settings_size
        loaded_size = 0

        for _ in self.load_settings(level, settings_data):
            loaded_size += 1
            yield loaded_size/total_file_size

        for _ in self.load_terrain(level, terrain_data):
            loaded_size += 1
            yield loaded_size / total_file_size 

        for _, layers in level.terrain.items():
            for __, tile in layers.items():
                level.check_neighboring_tiles(tile)
                loaded_size += 1
                yield loaded_size / total_file_size

        for _ in self.load_objects(level, objects_data):
            loaded_size += 1
            yield loaded_size / total_file_size
        yield loaded_size / total_file_size

    def load_objects(self, level : Level, data : dict):
        for _, kwargs in data.items():
            object_class = self.assets.object_assets[kwargs['type']]['class']
            object : GameObject = object_class(**kwargs, level= level)    
            level.add_object_to_queue(object)
            yield
            
    def load_terrain(self, level : Level, data : dict):
        level.screens = [pygame.Surface((self.app.SCREEN_WIDTH, self.app.SCREEN_HEIGHT), flags= pygame.SRCALPHA).convert_alpha() for _ in range(level.layers)]
        for screen in level.screens: screen.set_colorkey((0,0,0))
        tiles_data = data['tiles']

        for x in range(level.world_width):
            for y in range(level.world_height):
                level.terrain[(x, y)] = {}
                for layer in range(level.layers):
                    key = f'{x},{y}'
                    id = (x, y)
                    pos = Vector2(x * level.tile_size, y * level.tile_size)
                    coll = tiles_data[key][f'{layer}']['coll']
                    variation = tiles_data[key][f'{layer}']['variation']
                    type = tiles_data[key][f'{layer}']['type']
                    tile = Tile(pos, type, coll, variation, id, layer, level)
                    level.terrain[(x, y)][layer] = tile
                    level.spaces[tile.layer].add(tile.body, tile.shape)
                    yield

    def load_settings(self, level: Level, data : dict):
        level.settings['saved_settings'] = {}
        for key, value in data.items():
            level.settings['saved_settings'].update(**{key: value})
            yield

    def finished_loading_resources(self, level, level_path):
        self.levels[level_path] = level
        self.initialize()

    def get_level_loaded_percentage(self):
        if self.current_level:
            return self.current_level.loaded_percentage
        else:
            return 0
    
    def save_current_level(self):
        lock = threading.Lock()
        with lock:
            if not self.saving:
                self.saving = True     
                saving_thread = threading.Thread(target= lambda: self.run_saving_thread(self.current_level, self.finished_saving))
                saving_thread.start()

    def run_saving_thread(self, level: Level, callback):
        try:
            for percent in self.save_level(level):
                level.saved_percentage = percent * 100
        except StopIteration:
            if level.saved_percentage != 100:
                level.saved_percentage = 100
        if callable(callback):
            callback()

    def save_level(self, level : Level):
        directory = 'data/Levels/'
        terrain_path = os.path.join(directory, level.name, 'terrain.json')
        objects_path = os.path.join(directory, level.name, 'objects.json')  
        settings_path = os.path.join(directory, level.name, 'settings.json')
        objects_file_size = len(level.game_objects)
        terrain_file_size = level.world_width * level.world_height * level.layers
        settings_file_size = len(level.settings['saved_settings'])
        total_file_size = terrain_file_size + objects_file_size + settings_file_size
        loaded_size = 0

        for _ in self.save_settings(level, settings_path):
            loaded_size += 1
            yield loaded_size/total_file_size
        for _ in self.save_terrain(level, terrain_path):
            loaded_size += 1
            yield loaded_size/total_file_size
        for _ in self.save_objects(level, objects_path):
            loaded_size += 1
            yield loaded_size/total_file_size

        yield loaded_size/total_file_size

    def finished_saving(self):
        self.saving = False
        print('callback worked')

    def save_terrain(self, level : Level, terrain_path):
        cache = {
            "width": level.world_width,
            "height": level.world_height,
            "tileSize": level.tile_size,
            "layers": level.layers,
        }

        # Open the file and start writing the JSON structure
        with open(terrain_path, "w") as file:
            file.write("{\n")
            file.write("\"cache\": ")
            json.dump(cache, file, indent=4)
            file.write(",\n\"tiles\": {\n")
            first_tile = True  
            for x in range(cache["width"]):
                for y in range(cache["height"]):
                    key = f"{x},{y}"
                    if not first_tile:
                        file.write(",\n")
                    first_tile = False
                    file.write(f"\"{key}\": {{\n")
                    for layer in range(cache["layers"]):
                        tile_data = level.terrain.get((x, y)).get(layer).ToDict()
                        if layer < cache["layers"] - 1:
                            file.write(f"  \"{layer}\": {json.dumps(tile_data)},\n")
                        else:
                            file.write(f"  \"{layer}\": {json.dumps(tile_data)}\n")
                        yield
                    file.write("}")
            file.write("\n}\n}")
            yield

    def save_objects(self, level : Level, object_path):
        with open(object_path, 'w') as file:
            file.write("{\n")
            index = 0
            for _, game_object in enumerate(level.game_objects):
                if object_dict := game_object.ToDict():
                    object_json = json.dumps(object_dict)
                    if index > 0:
                        file.write(f",  \"{index}\": {object_json}")
                        file.write("\n")
                    else:
                        file.write(f"  \"{index}\": {object_json}")
                        file.write("\n")
                    yield  
                else:
                    index -= 1
                    yield
                index+= 1
            file.write("}")

    def save_settings(self, level : Level, settings_path):
        with open(settings_path, 'w') as file:
            file.write("{")
            for index, (key, value) in enumerate(level.settings['saved_settings'].items()):
                if index > 0:
                    file.write(f",  \"{key}\": {value}")
                else:
                    file.write(f"  \"{key}\": {value}")
                yield      
            file.write("}")

    def get_level_saved_percentage(self):
        if self.current_level:
            return self.current_level.saved_percentage
        else:
            return 0
    
    def update(self, deltatime):
        self.update_generator_tasks()
        self.update_settings()
        self.editor.update(deltatime)
        if self.current_level:
            self.current_level.update(deltatime)
         
    def update_settings(self):
        pass

    def update_generator_tasks(self):
        for key, task in self.generatorTasks.items():
            try:    
                returned_task = next(task)
            except StopIteration:
                task = None
                pass

    def refactor_editor(self, edit_type, type, object_class, object_args):
        self.editor.edit_type = edit_type
        self.editor.type = type
        self.editor.object_class = object_class
        self.editor.object_args = object_args
        self.editor.update_tile_image(type)
        self.editor.update_object_image(type)

    def fade_in(self):
        fade_steps = self.settings['fade_steps']
        for i in range(fade_steps):
            self.settings['game_transition_weight'] = i/fade_steps
            yield 
        self.settings['game_transition_weight'] = 1
        yield

    def fade_out(self):
        fade_steps = self.settings['fade_steps']
        for i in range(fade_steps):
            self.settings['game_transition_weight'] = 1 - i/fade_steps
            yield 
        self.settings['game_transition_weight'] = 0
        yield

    def close(self, events = None):
        self.input.EditorAction.active = False
        self.editor.close()
        self.current_level.close()
        self.current_level = None
        self.active = False
        if isinstance(events, Iterable):
            for event in events:
                if callable(event):
                        event()



class AssetsManager:

    def __init__(self, app):
        from Shader import Shader
        self.app = app
        self.coll_types = {'coll_types' :lambda :CTYPES.__dict__}
        self.create_collision_types()
        self.object_assets = self.load_object_assets()
        self.tile_assets = self.load_tile_assets()
        self.background_assets = self.load_background_assets()
        self.auto_tile_map = self.load_auto_tile_map()
        #self.textures = {'perlin_noise': Shader.surf_to_texture_class(self.app.ctx, pygame.image.load('shader_programs/textures/perlin_noise.png').convert_alpha())}
        #self.textures['perlin_noise'].use(21)

    def create_collision_types(self):
        from pymunk import ShapeFilter  # Ensure you're using Pymunk's collision system

        CTYPES.nothing = 0 
        CTYPES.terrain = 1 << 0
        CTYPES.enemy = 1 << 1
        CTYPES.particle = 1 << 2
        CTYPES.platform = 1 << 3
        CTYPES.collectable = 1 << 4
        CTYPES.liquid = 1 << 5
        CTYPES.player = 1 << 6
        CTYPES.liquid_body << 7
        print(CTYPES.__dict__.items())

    def load_auto_tile_map(self):
        return {
        tuple(['same', 'same', 'same','same',]) : (0,0),
        tuple(['same', 'same', 'same','other',]) : (1,0),
        tuple(['same', 'same', 'other','same',]) : (-1,0),
        tuple(['other', 'same', 'same','other',]) : (1,1),
        tuple(['other', 'same', 'other','same',]) : (-1,1),
        tuple(['other', 'same', 'same','same',]) : (0,1),
        tuple(['same', 'other', 'same','other',]) : (1,-1),
        tuple(['same', 'other', 'other','same',]) : (-1,-1),
        tuple(['same', 'other', 'same','same',]) : (0,-1),
    }

    def load_background_assets(self):
        from Shader import Shader
        assets = {'background_textures' : None}
        surfs = []
        count = 0
        for file in os.listdir(f'data\Assets\Backgrounds'):
                img = pygame.image.load(f'data\Assets\Backgrounds/{file}').convert_alpha()
                surfs.append(img)
                count += 1
        assets['background_textures'] = Shader.surfaces_to_texture_array(self.app.ctx, surfs)
        assets['background_textures'].use(10)
        assets['num_textures'] = count
        return assets

    def load_object_assets(self):
        assets = {}

        def getFruits():
            assets = {}
            fruit_names = os.listdir('data\Assets\Objects\Fruits')
            collected_tilesheet = pygame.image.load(f'data\Assets\Objects\Fruits\Collected.png').convert_alpha()
            for fruit in fruit_names:
                fruit_type = fruit.replace('.png', '')
                tilesheet = pygame.image.load(f'data\Assets\Objects\Fruits\{fruit_type}.png').convert_alpha()            
                assets[fruit_type] = {
                    'class' : Fruit,
                    'default_frames' : self.get_frames(tilesheet, 32, 32, width_pad= 4, height_pad= 4),
                    'collected_frames': self.get_frames(collected_tilesheet, 32, 32, width_pad= 4, height_pad= 4),
                    'standstill' : None, 
                    'scale' : 1,
                    'size' : lambda level: [level.tile_size, level.tile_size],
                    'offset' : Vector2(0,0),
                    'elasticity' : 0.5,
                    'friction' : 0.8,
                    'mass' : 10,
                    'shape_type': 'circle',
                    'body_type' : pymunk.Body.DYNAMIC,
                    'moment' : lambda mass, radius: pymunk.moment_for_circle(mass, 0, radius),
                    'radius' : lambda level, scale: level.tile_size * scale,
                    'shape' : lambda body, radius: pymunk.Circle(body, radius),
                    'categories' : CTYPES.collectable,
                    'mask' : CTYPES.collide_with([CTYPES.terrain, CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])
                    }
                assets[fruit_type]['standstill'] = assets[fruit_type]['default_frames'][0]
            return assets
        
        def getFire():
            assets = {}
            hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Fire/Hit (16x32).png').convert_alpha()
            off_sheet = pygame.image.load('data/Assets/Objects/Traps/Fire/Off.png').convert_alpha()
            on_sheet = pygame.image.load('data/Assets/Objects/Traps/Fire/On (16x32).png').convert_alpha()

            assets['Fire'] = {
                'class' : Fire,
                'activate_frames' : self.get_frames(hit_sheet, 16, 32),
                'deactivate_frames' : self.get_frames(hit_sheet, 16, 32, reverse= True),
                'on_frames' : self.get_frames(on_sheet, 16, 32),
                'off_frames' : [off_sheet],
                'scale' : 1,
                'size' : lambda level: [level.tile_size, level.tile_size],
                'offset' : lambda level: Vector2(0, -level.tile_size/4),
                'standstill' : off_sheet.subsurface((0,16,16,16)),
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 100,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.DYNAMIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 2.5,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.enemy,
                    'mask' : CTYPES.collide_with([CTYPES.terrain, CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])
            }
           
            return assets
        
        def getSpike():
            assets = {}
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Spikes/Idle.png').convert_alpha()

            assets['Spike'] = {
                'class' : Spike,
                'idle_frames' : idle_sheet,
                'scale' : 1,
                'size' : lambda level: [level.tile_size, level.tile_size],
                'offset' : Vector2(0,0),
                'standstill' : idle_sheet,
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 10,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.enemy,
                    'mask' : CTYPES.collide_with([CTYPES.terrain, CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])
            }
            return assets
        
        def getRockHead():
            assets = {}
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Idle.png').convert_alpha()
            bottom_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Bottom Hit (42x42).png').convert_alpha()
            top_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Top Hit (42x42).png').convert_alpha()
            right_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Right Hit (42x42).png').convert_alpha()
            left_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Left Hit (42x42).png').convert_alpha()
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Idle.png').convert_alpha()
            blink_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Blink (42x42).png').convert_alpha()

            assets['RockHead'] = {
                'class' : RockHead,
                'idle_frames' : [idle_sheet],
                'bottom_hit_frames' : self.get_frames(bottom_hit_sheet, 42, 42),
                'top_hit_frames' : self.get_frames(top_hit_sheet, 42, 42),
                'left_hit_frames' : self.get_frames(left_hit_sheet, 42, 42),
                'right_hit_frames' : self.get_frames(right_hit_sheet, 42, 42),
                'blink_frames' : self.get_frames(blink_sheet, 42, 42),
                'scale' : 2,
                'size' : lambda level: [level.tile_size, level.tile_size],
                'offset' : Vector2(0,0),
                'standstill' : idle_sheet,
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 200,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.collide_with([CTYPES.enemy]),
                    'mask' : CTYPES.collide_with([CTYPES.terrain, CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.liquid])
            }
            
            return assets

        def getSpikeHead():
            assets = {}
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Idle.png').convert_alpha()
            bottom_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Bottom Hit (54x52).png').convert_alpha()
            top_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Top Hit (54x52).png').convert_alpha()
            right_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Right Hit (54x52).png').convert_alpha()
            left_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Left Hit (54x52).png').convert_alpha()
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Idle.png').convert_alpha()
            blink_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Blink (54x52).png').convert_alpha()

            assets['SpikeHead'] = {
                'class' : RockHead,
                'idle_frames' : [idle_sheet],
                'bottom_hit_frames' : self.get_frames(bottom_hit_sheet, 54, 52),
                'top_hit_frames' : self.get_frames(top_hit_sheet, 54, 52),
                'left_hit_frames' : self.get_frames(left_hit_sheet, 54, 52),
                'right_hit_frames' : self.get_frames(right_hit_sheet, 54, 52),
                'blink_frames' : self.get_frames(blink_sheet, 54, 52),
                'scale' : 2.5,
                'size' : lambda level: [level.tile_size, level.tile_size],
                'offset' : Vector2(0,0),
                'standstill' : idle_sheet,
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 200,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.enemy,
                    'mask' : CTYPES.collide_with([CTYPES.terrain,CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.liquid])
            }
            return assets
       
        def getSaw():
            assets = {}
            off_sheet = pygame.image.load('data/Assets/Objects/Traps/Saw/Off.png').convert_alpha()
            on_sheet = pygame.image.load('data/Assets/Objects/Traps/Saw/On (38x38).png').convert_alpha()
            assets['Saw'] = {
                'class' : Saw,
                'on_frames' : self.get_frames(on_sheet, 38, 38),
                'off_frames' : [off_sheet],
                'scale' : 2,
                'size' : lambda level: [level.tile_size, level.tile_size],
                'offset' : Vector2(0,0),
                'standstill' : off_sheet,
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 200,
                    'shape_type': 'circle',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, radius: pymunk.moment_for_circle(mass, 0, radius),
                    'radius' : lambda level, scale: level.tile_size * scale,
                    'shape' : lambda body, radius: pymunk.Circle(body, radius),
                    'categories' : CTYPES.enemy,
                    'mask' : CTYPES.collide_with([CTYPES.terrain, CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])
            }
            return assets
        
        def getParticles():
            assets = {}
            standstill = pygame.image.load('data\Assets\Objects\Particles\Dust Particle.png').convert_alpha()

            
            assets['Particle'] = {
                'class' : Particle,
                'color' : (135,206,235),
                'scale' : 0.25,
                'size' : lambda level: [level.tile_size, level.tile_size],
                'offset' : Vector2(0,0),
                'standstill' : standstill,
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 1,
                    'shape_type': 'circle',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, radius: pymunk.moment_for_circle(mass, 0, radius),
                    'radius' : lambda level, scale : level.tile_size * scale,
                    'shape' : lambda body, radius: pymunk.Circle(body, radius),
                    'categories' : CTYPES.particle,
                    'mask' : CTYPES.collide_with([])
            }
            return assets

        def getSpring():
            assets = {}
            standstill = pygame.image.load('data/Assets/Objects/Traps/Trampoline/Idle.png').convert_alpha()
            jump_sheet = pygame.image.load('data/Assets/Objects/Traps/Trampoline/Jump (28x28).png').convert_alpha()
            assets['Spring'] = {
                'class' : Spring,
                'scale' : 1,
                'size' : lambda level: [level.tile_size, level.tile_size],
                'offset' : Vector2(0,0),
                'standstill' : standstill,
                'idle_frames' : [standstill],
                'activate_frames' : self.get_frames(jump_sheet, 28, 28),
                'deactivate_frames' : self.get_frames(jump_sheet, 28, 28, reverse = True),
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 50,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.platform,
                    'mask' : CTYPES.collide_with([CTYPES.enemy, CTYPES.player, CTYPES.collectable])
                }
            assets['Spring']['on_frames'] = [assets['Spring']['activate_frames'][len(assets['Spring']['activate_frames']) - 1]]

            return assets

        def getPlatforms():
            assets = {}
            for platform in ['Brown', 'Grey']:
                on_frames = pygame.image.load(f'data/Assets/Objects/Traps/Platforms/{platform} Off.png').convert_alpha()
                off_frames = pygame.image.load(f'data/Assets/Objects/Traps/Platforms/{platform} Off.png').convert_alpha()
                assets[platform] = {
                    'class' : PlatForm,
                    'scale' : 2,
                    'size' : lambda level: [level.tile_size, level.tile_size/4],
                    'offset' : Vector2(0,0),
                    'standstill' : off_frames,
                    'on_frames' : self.get_frames(on_frames, 32, 8),
                    'off_frames' : self.get_frames(off_frames, 32, 8),
                    'elasticity' : 0.0,
                    'friction' : 1.0,
                    'mass' : 50,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.platform,
                    'mask' : CTYPES.collide_with([CTYPES.enemy, CTYPES.player, CTYPES.collectable])
                    }
            return assets
        
        def getRain():
            assets = {}
            standstill = pygame.Surface((32,32)).convert_alpha()
            assets['Rain'] = {
                'class' : Rain,
                'color' : (135,206,235),
                'scale' : 1,
                'size' : lambda level: [level.tile_size/randint(6, 9), level.tile_size/randint(2, 4)],
                'offset' : Vector2(0,0),
                'standstill' : standstill,
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 2,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.DYNAMIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.particle,
                    'mask' : CTYPES.collide_with([CTYPES.terrain, CTYPES.liquid])

            }
            standstill.fill(assets['Rain']['color'])
            return assets

        def get_liquids():
            from Shader import Shader
            assets = {}
            
            lava_surf = pygame.image.load('shader_programs/textures/lava_texture1.png').convert_alpha()
            water_surf = pygame.image.load('data\Assets\Terrain\waterTile.jpg').convert_alpha()
            surfs = [water_surf, lava_surf]
            for index, surf in enumerate(surfs):
                surfs[index] = pygame.transform.smoothscale(surf, (100,100))
            texture_array = Shader.surfaces_to_texture_array(self.app.ctx, surfs)            
            texture_array.use(20)
            liquids = {'Water' : 0, 'Lava' : 1}
            for liquid, texture_index in liquids.items():          
                assets[liquid] = {
                    'class' : Liquid,
                    'standstill' : surfs[texture_index], 
                    'texture_index' : texture_index,
                    'color' : [255, 0, 255, 255],
                    'scale' : 5,
                    'size' : lambda level: [level.tile_size, level.tile_size],
                    'offset' : Vector2(0,0),
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 100,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.STATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.liquid,
                    'mask' : CTYPES.collide_with([CTYPES.enemy, CTYPES.player, CTYPES.collectable])
                    }
            return assets
        
        def get_liquid_nodes():
            assets = {}
                   
            assets['Liquid_Node'] = {
                    'class' : Liquid.Node,
                    'standstill' : None, 
                    'scale' : 1/5,
                    'size' : lambda level: [level.tile_size, level.tile_size],
                    'offset' : Vector2(0,0),
                    'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 50,
                    'shape_type': 'circle',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, radius: pymunk.moment_for_circle(mass, 0, radius),
                    'radius' : lambda level, scale: level.tile_size * scale,
                    'shape' : lambda body, radius: pymunk.Circle(body, radius),
                    'categories' : CTYPES.liquid,
                    'mask' : CTYPES.collide_with([CTYPES.enemy, CTYPES.player, CTYPES.collectable])
                    }
            surf = pygame.Surface((50, 50)).convert_alpha()
            surf.set_colorkey((0,0,0, 0))
            surf.fill((0,0,0, 0))
            pygame.draw.circle(surf, (0, 0, 255), surf.get_rect().center, 30)
            assets['Liquid_Node']['standstill'] = surf
            return assets
        
        def get_pendulum():
            assets = {}
            tilesheet = pygame.image.load('data\Assets\Objects\Traps\Spiked Ball\Spiked Ball.png').convert_alpha()
            assets['Pendulum'] = {
                    'class' : Pendulum,
                    'idle_frames' : [tilesheet],
                    'standstill' : tilesheet, 
                    'scale' : 2,
                    'size' : lambda level: [level.tile_size, level.tile_size],
                    'offset' : Vector2(0,0),
                    'elasticity' : 0.5,
                    'friction' : 0.8,
                    'mass' : 200,
                    'shape_type': 'circle',
                    'body_type' : pymunk.Body.DYNAMIC,
                    'moment' : lambda mass, radius: pymunk.moment_for_circle(mass, 0, radius),
                    'radius' : lambda level, scale: level.tile_size * scale,
                    'shape' : lambda body, radius: pymunk.Circle(body, radius),
                    'categories' : CTYPES.enemy,
                    'mask' : CTYPES.collide_with([CTYPES.terrain, CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])
                    }
            return assets

        def get_grass_generators():
            assets = {}
            grass_types = {'green' : (175, 235, 20), 'orange' : (225, 175, 35)}
            for type, color in grass_types.items():
                img = pygame.Surface((10,10)).convert_alpha()
                img.fill(color)
                assets[type] = {
                    'class' : Grass_Generator,
                    'scale' : 1,
                    'size' : lambda level: [level.tile_size, level.tile_size],
                    'offset' :  Vector2(0, 0),
                    'color' : color,
                    'standstill' : img,
                    'elasticity' : 0.0,
                    'friction' : 1.0,
                    'mass' : 50,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.particle,
                    'mask' : CTYPES.collide_with([])
                    }
            return assets

        def get_grass():
            assets = {}
            grass_imgs = [pygame.image.load(f'data/Assets/Grass/grass{index}.png').convert_alpha() for index in range(1, 6)] 
        
            assets['Grass'] = {
                    'class' : Grass,
                    'scale' : 1.25,
                    'size' : lambda level: [level.tile_size, level.tile_size],
                    'offset' : Vector2(0,0),
                    'standstill' : grass_imgs[0],
                    'img_variations' : grass_imgs,
                    'elasticity' : 0.0,
                    'friction' : 1.0,
                    'mass' : 50,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.particle,
                    'mask' : CTYPES.collide_with([])
                    }
            return assets
        
        def get_fan():
            assets = {}
            on_tilesheet = pygame.image.load(f'data\Assets\Objects\Traps\Fan\On (24x8).png').convert_alpha()
            off_tilesheet = pygame.image.load(f'data\Assets\Objects\Traps\Fan\Off.png').convert_alpha()
        
            assets['Fan'] = {
                    'class' : Fan,
                    'scale' : 1.5,
                    'size' : lambda level: [level.tile_size * 1.25, level.tile_size/2],
                    'offset' : Vector2(0,0),
                    'standstill' : off_tilesheet,
                    'off_frames' : self.get_frames(off_tilesheet, 24, 8),
                    'on_frames' : self.get_frames(on_tilesheet, 24, 8),
                    'elasticity' : 0.0,
                    'friction' : 1.0,
                    'mass' : 50,
                    'shape_type': 'poly',
                    'body_type' : pymunk.Body.KINEMATIC,
                    'moment' : lambda mass, size: pymunk.moment_for_box(mass, size),
                    'radius' : 0.25,
                    'shape' : lambda body, size, radius: pymunk.Poly.create_box(body, size, radius),
                    'categories' : CTYPES.particle,
                    'mask' : CTYPES.collide_with([])
                    }
            return assets

        
        assets.update(**getFruits())
        assets.update(**getFire())
        assets.update(**getSpike())
        assets.update(**getRockHead())
        assets.update(**getSpikeHead())
        assets.update(**getSaw())
        assets.update(**getParticles())
        assets.update(**getSpring())
        assets.update(**getPlatforms())
        assets.update(**getRain())
        assets.update(**get_liquids())
        assets.update(**get_liquid_nodes())
        assets.update(**get_pendulum())
        assets.update(**get_grass_generators())
        assets.update(**get_grass())
        assets.update(**get_fan())
        return assets

    def load_tile_assets(self):
        tilesheet = pygame.image.load('data/Assets/Terrain/Terrain (16x16).png').convert_alpha()
        tilesheet2 = pygame.image.load('data\Assets\Terrain\Sand Mud Ice (16x6).png').convert_alpha()
        watersheet = pygame.image.load('data\Assets\Terrain\waterTile.jpg').convert_alpha()
        watersheet = pygame.transform.smoothscale(watersheet, (48,48))
        watersheet.set_alpha(200)
        def extract_tiles(terrain):
            return {
                (0, 0): terrain.subsurface(pygame.Rect(16, 16, 16, 16)),  # center
                (-1, 0): terrain.subsurface(pygame.Rect(0, 16, 16, 16)),  # left
                (1, 0): terrain.subsurface(pygame.Rect(32, 16, 16, 16)),  # right
                (-1, 1): terrain.subsurface(pygame.Rect(0, 0, 16, 16)),   # topleft
                (1, 1): terrain.subsurface(pygame.Rect(32, 0, 16, 16)),   # topright
                (0, 1): terrain.subsurface(pygame.Rect(16, 0, 16, 16)),   # top
                (-1, -1): terrain.subsurface(pygame.Rect(0, 32, 16, 16)), # bottomleft
                (0, -1): terrain.subsurface(pygame.Rect(16, 32, 16, 16)), # bottom
                (1, -1): terrain.subsurface(pygame.Rect(32, 32, 16, 16)), # bottomright
            }

        assets = {}
        i = 0
        for key in ['green_grass', 'orange_grass', 'pink_grass']:
            try:
                assets[key] = {"full": self.get_terrain_images(tilesheet, 96, i, 16),
                               'elasticity' : 0.6,
                    'friction' : 0.8,
                    'mass' : 200,
                    'categories' : CTYPES.terrain,
                    'mask' : CTYPES.collide_with([CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])}
                assets[key]['split'] = extract_tiles(assets[key]['full'])
                i+= 64
            except:
                break
        assets['sand'] = {"full": self.get_terrain_images(tilesheet2, 0, 0, 16),
                               'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 200,
                    'categories' : CTYPES.terrain,
                    'mask' : CTYPES.collide_with([CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])}
        assets['sand']['split'] = extract_tiles(assets['sand']['full'])
        assets['mud'] = {"full": self.get_terrain_images(tilesheet2, 64, 0, 16),
                               'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 200,
                    'categories' : CTYPES.terrain,
                    'mask' : CTYPES.collide_with([CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])}
        assets['mud']['split'] = extract_tiles(assets['mud']['full'])
        assets['ice'] = {"full": self.get_terrain_images(tilesheet2, 128, 0, 16),
                               'elasticity' : 0.2,
                    'friction' : 0.05,
                    'mass' : 200,
                    'categories' : CTYPES.terrain,
                    'mask' : CTYPES.collide_with([CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])}
        assets['ice']['split'] = extract_tiles(assets['ice']['full'])
        assets['water'] = {'full' : watersheet,
                               'elasticity' : 0.2,
                    'friction' : 0.8,
                    'mass' : 200,
                    'categories' : CTYPES.terrain,
                    'mask' : CTYPES.collide_with([CTYPES.collectable, CTYPES.enemy, CTYPES.player, CTYPES.platform, CTYPES.liquid])}
        assets['water']['split'] = extract_tiles(assets['water']['full'])
        assets['empty'] = {'full' : None, 'split' : None,
                               'elasticity' : 0.1,
                    'friction' : 0.8,
                    'mass' : 1,
                    'categories' : CTYPES.nothing,
                    'mask' : CTYPES.collide_with([CTYPES.nothing])}
        return assets

    def get_terrain_images(self, tilesheet, x, y, size):
        return pygame.Surface.subsurface(tilesheet, pygame.Rect(x, y, size * 3, size * 3))

    def get_frames(self, tilesheet : pygame.Surface, width, height,
                    width_pad = 0, height_pad = 0, left_pad = 0, right_pad = 0,
                        top_pad = 0, bottom_pad = 0, reverse = False):
            frames = []
            
            iterations = int(tilesheet.get_width() / width)
            for x in range(iterations):
                frame = tilesheet.subsurface(x * width + width_pad + left_pad, height_pad + top_pad, width - width_pad * 2 - right_pad, height - height_pad * 2 - bottom_pad)
                frames.append(frame)
            if reverse:
                frames.reverse()
            return frames
    


