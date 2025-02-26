import pygame
import threading
from array import array
import time 
import pygame.gfxdraw
from pygame.math import Vector2
import multiprocessing
import json
import os

import pymunk.pygame_util
from Tile import Tile
from Input import InputHandler
from Camera import Camera
import math
from Editor import Editor
from particles import *
from random import *
from objects import *
from collision_categories import Collision_Types, CTYPES
import objects
import pygame.gfxdraw
import numpy
import pymunk 

class GameManager:
    WORLD_WIDTH = None
    WORLD_HEIGHT = None
    TILE_SIZE = None
    LAYERS = None    
    BRIGHTNESS = None
    GRAVITY = 200

    AUTO_TILE_MAP = {
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

    TILE_TYPES = {'green_grass' : None,
                   'pink_grass': None,
                    'orange_grass': None,
                    'mud' : None,
                    'sand' : None,
                    'ice' : None,
                    'water' : None}
    OBJECT_TYPES = {
        
    }

    def __init__(self, app) -> None:
        self.app = app
        self.screens = [pygame.Surface((app.SCREEN_WIDTH, app.SCREEN_HEIGHT), flags= pygame.SRCALPHA).convert_alpha()]
        self.gameObjects = []
        self.staticObjects = {}
        self.terrain = {}
        self.terrain_images = self.LoadImages()
        self.active = True
        self.paused = False
        self.progress = 0
        self.input : InputHandler = self.app.input
        self.camera = Camera(self.input)
        self.editor = Editor(self)
        self.spaces = []
        GameManager.TILE_TYPES = self.GetTiles()
        GameManager.OBJECT_TYPES = self.GetObjects()
        self.start_x, self.start_y = 0,0
        self.range_x, self.range_y = 0,0
        self.levelName = None
        self.generatorTasks = {}
        self.settings = {'game_transition_weight' : 1}
        self.fade_steps = 30
        self.saving = False
        self.selectedLayer = 1
        self.lightsource_data = [[0.0]*8] * 100
        self.watertile_data =  [[0.0] * 2] * 100
        self.simulation_steps = 50


    def update(self, deltatime):
        
        for screen in self.screens:
            screen.fill((0,0,0,0))
        self.camera.update(deltatime)
        self.editor.update(deltatime)
        self.updateGameObjects(deltatime)
        self.updateSettings()
        self.GeneratorTasks()
        for _ in range(self.simulation_steps):
            self.space.step(deltatime/self.simulation_steps)
        self.RemoveObjects()

        self.render()
        GameObject.QUEUE = []
    
    def Initialize(self):
        print('Initializing')
        self.generatorTasks['fade_out'] = self.fade_out()
        self.camera.pos = Vector2(0,0)
        self.editor.Initialize()
        self.input.EditorAction.active = True
        
        for object in self.gameObjects:
            object.Initialize()
        

    def fade_in(self):
        for i in range(self.fade_steps):
            self.settings['game_transition_weight'] = i/self.fade_steps
            yield 
        self.settings['game_transition_weight'] = 1
        yield

    def fade_out(self):
        for i in range(self.fade_steps):
            self.settings['game_transition_weight'] = 1 - i/self.fade_steps
            yield 
        self.settings['game_transition_weight'] = 0
        yield

    def updateGameObjects(self, deltatime):
        self.lightsource_data = [[0.0] * 8] * 100
        removeObjects = [gameObject for gameObject in self.gameObjects if gameObject.remove]
        for gameObject in removeObjects:
            self.space.remove(gameObject.shape, gameObject.body)

        lightsources = [gameObject for gameObject in self.gameObjects if isinstance(gameObject, LightSource)]
        for gameObject in self.gameObjects:
            gameObject.idle(deltatime)
        
        for index, lightsource in enumerate(lightsources):
            if index < 100:
                self.lightsource_data[index] = lightsource.ToData()
               
            

    def RemoveObjects(self):
        removeObjects = [gameObject for gameObject in self.gameObjects if gameObject.remove]
        for gameObject in removeObjects:
            self.gameObjects.remove(gameObject)



    def GeneratorTasks(self):
        for key, task in self.generatorTasks.items():
            try:    
                next(task)
            except StopIteration:
                task = None


    def Pop(self, object):
        if object:
            object.remove = True

            color = pygame.Color(pygame.transform.average_color(object.img))
        else:
            color = pygame.Color(255,255,255,255)

        for i in range(30):
            val = randint(0, 10)
            color += pygame.Color(val, val, val, val)
            velocity = Vector2(random() * randint(-200,200),random() * -300)
            self.gameObjects.append(DefaultParticle(Vector2(object.rect.center), Vector2(0,0),'Particle',object.layer, self,  velocity, color))

    def SetEditorType(self, edit_type, type, object_class, object_args):
        self.editor.edit_type = edit_type
        self.editor.type = type
        self.editor.object_class = object_class
        self.editor.object_args = object_args
        self.editor.updateTileImage(type)
        self.editor.updateObjectImage(type)


    def render(self):
        self.Optimize()
        tiles = self.GetOnScreenTiles()
        for tile in tiles:
            tile : Tile
            if tile.img:
                self.screens[tile.layer].blit(tile.img, tile.rect.topleft - self.camera.pos)
        if self.editor.img:
            self.screens[self.editor.layer].blit(self.editor.img, self.editor.rect.topleft - self.camera.pos + self.editor.object_offset)
        for object in self.gameObjects:
            if object.img:
                self.screens[object.layer].blit(object.img, object.rect.topleft - self.camera.pos)
            if isinstance(object, PathFollower):
                pygame.gfxdraw.rectangle(self.screens[object.layer], pygame.Rect((object.pathRect.topleft - self.camera.pos),object.pathRect.size), (255,255,255))
            if object.layer == self.editor.layer:
                if self.editor.eraser_rect.contains(object.rect):
                    pygame.gfxdraw.rectangle(self.screens[self.selectedLayer], pygame.Rect((object.rect.topleft - self.camera.pos),object.rect.size), (255,255,255))
        pygame.gfxdraw.rectangle(self.screens[self.selectedLayer], self.editor.onScreen_path_rect, (255,255,255))
        pygame.gfxdraw.rectangle(self.screens[self.selectedLayer], self.editor.onScreen_eraser_rect, (255,255,255))
        
        self.settings['tile_size'] = GameManager.TILE_SIZE
        self.settings['td_length'] = len(self.watertile_data)
        self.settings['water_tile_data'] = array('f', [data for id in self.watertile_data for data in id])
        self.settings['camera_pos'] = array('f', [self.camera.pos.x, self.camera.pos.y])

    
    def Optimize(self):
        self.start_x = int(math.floor(self.camera.pos.x / self.TILE_SIZE))
        self.start_y = int(math.floor(self.camera.pos.y / self.TILE_SIZE))
        self.range_x = int(math.ceil(self.camera.pos.x / self.TILE_SIZE + self.app.SCREEN_WIDTH / self.TILE_SIZE))
        self.range_y = int(math.ceil(self.camera.pos.y / self.TILE_SIZE + self.app.SCREEN_HEIGHT / self.TILE_SIZE))

    def Exit(self, events):
        self.input.EditorAction.active = False
        self.generatorTasks = {'fade_in' : self.fade_in()}
        self.terrain = {}
        self.space.remove(*self.space.shapes)
        self.space.remove(*self.space.bodies)
        self.gameObjects = []
        for i in range(self.fade_steps):
            yield
        for event in events:
            if callable(event):
                    print(event)
                    event()

        self.active = False
        yield
            

    def GetOnScreenTiles(self):
        tiles = []
        self.watertile_data = [[0.0] * 2] * 100
        count = 0
        for x in range(self.start_x, self.range_x):
            for y in range(self.start_y, self.range_y):
                for layer in range(self.LAYERS):
                    row = self.terrain.get((x,y))
                    if row:
                        tile = row.get(layer)
                        if tile:
                            tiles.append(tile)
                            if tile.type == 'water':
                                if count < 100:
                                    self.watertile_data[count] = list(tile.id)
                                    count+= 1
        return tiles
    
    def updateSettings(self):
        self.settings['lightsources'] = array('f', [data for list in self.lightsource_data for data in list])
        self.settings['ls_length'] = len(self.lightsource_data)
    
    def AutoTile(self):
        tiles = self.GetOnScreenTiles()
        for tile in tiles:
            self.CheckNeighbors(tile)

                
    def CheckNeighbors(self, tile):
        if tile.type != 'empty':
            layered_neighbors = [self.terrain.get(tuple(tile.id + Vector2(0,-1))), self.terrain.get(tuple(tile.id + Vector2(0,1))), self.terrain.get(tuple(tile.id + Vector2(-1,0))), self.terrain.get(tuple(tile.id + Vector2(1,0)))]

            neighbors = []

            for row in layered_neighbors:
                if row:
                    neighbors.append(row.get(tile.layer))
                else:
                    neighbors.append(None)

            list = []
            for neighbor in neighbors:
                if neighbor:
                    if neighbor.type == tile.type:
                        list.append('same')
                    else:
                        list.append('other')
                else:
                    list.append('other')

            if  tuple(list) in self.AUTO_TILE_MAP:
                tile.SetTo(tile.type, self.AUTO_TILE_MAP[tuple(list)])
    
    def GenerateResources(self, filePath):
        self.levelName = filePath
        directory = 'data/Levels/'
        terrain_path = os.path.join(directory, filePath, 'terrain.json')
        objects_path = os.path.join(directory, filePath, 'objects.json')
        settings_path = os.path.join(directory, filePath, 'settings.json')

        with open(terrain_path, 'r') as file:
            terrain_data = json.load(file)
        with open(objects_path, 'r') as file:
            objects_data = json.load(file)
        with open(settings_path, 'r') as file:
            settings_data = json.load(file)

        layers= terrain_data['cache']['layers']

        terrain_size = terrain_data['cache']['width'] * terrain_data['cache']['height'] * layers
        objects_size = len(objects_data)
        settings_size = len(settings_data)
        total_file_size = terrain_size * 2 + objects_size + settings_size
        loaded_size = 0

        for _ in self.GenerateSettings(settings_data):
            loaded_size += 1
            yield loaded_size/total_file_size

        for _ in self.GenerateTerrain(terrain_data):
            loaded_size += 1
            yield loaded_size / total_file_size 

        for key, layers in self.terrain.items():
            for layer, tile in layers.items():
                self.CheckNeighbors(tile)
                loaded_size += 1
                yield loaded_size / total_file_size

        for _ in self.GenerateObjects(objects_data):
            loaded_size += 1
            yield loaded_size / total_file_size
        yield loaded_size / total_file_size

    def GenerateSettings(self, settings_data : dict):
        self.settings['saved_settings'] = {}
        for key, value in settings_data.items():
            self.settings['saved_settings'].update(**{key: value})
            yield


    def GenerateTerrain(self, terrain_data):
        length = terrain_data['cache']['width'] * terrain_data['cache']['height'] * terrain_data['cache']['layers']
        GameManager.WORLD_WIDTH = terrain_data['cache']['width']
        GameManager.WORLD_HEIGHT = terrain_data['cache']['height']
        GameManager.TILE_SIZE = terrain_data['cache']['tileSize']
        GameManager.LAYERS = terrain_data['cache']['layers']
        self.screens = [pygame.Surface((self.app.SCREEN_WIDTH, self.app.SCREEN_HEIGHT), flags= pygame.SRCALPHA).convert_alpha() for _ in range(GameManager.LAYERS)]
        for screen in self.screens: screen.set_colorkey((0,0,0))
        tiles_data = terrain_data['tiles']
        progress = 0

        for x in range(self.WORLD_WIDTH):
            for y in range(self.WORLD_HEIGHT):
                self.terrain[(x, y)] = {}
                for layer in range(self.LAYERS):
                    key = f'{x},{y}'
                    id = (x, y)
                    pos = Vector2(x * self.TILE_SIZE, y * self.TILE_SIZE)
                    coll = tiles_data[key][f'{layer}']['coll']
                    variation = tiles_data[key][f'{layer}']['variation']
                    type = tiles_data[key][f'{layer}']['type']

                    tile = Tile(pos, type, coll, variation, id, layer, self)
                    self.terrain[(x, y)][layer] = tile
                    progress += 1
                    yield progress / length

    def GenerateObjects(self, objects_data):
        GameManager.OBJECT_TYPES = self.GetObjects()
        length = len(objects_data)  
        progress = 0

        for _, kwargs in objects_data.items():
            
                object_class = GameManager.OBJECT_TYPES[kwargs['type']]['class']
                print(object_class)
                object = object_class(**kwargs, manager= self)    
                self.gameObjects.append(object)
                self.space.add(object.body, object.shape)        
                progress += 1
                yield progress / length
                progress += 1
                yield progress / length

                continue


    def LoadLevel(self, filePath):
        self.space = pymunk.Space()
        self.space.gravity = (0, self.GRAVITY)
        self.gameObjects = []
        self.terrain = {}
        print(filePath)
        thread = threading.Thread(target=lambda: self.LoadResources(filePath, self.Initialize))
        
        thread.start()

    def LoadResources(self, filePath, callback):
        try:
            for percent in self.GenerateResources(filePath):
                self.progress = percent * 100
        except StopIteration:
            if self.progress != 100:
                self.progress = 100
                print("Could not load all assets")
        time.sleep(1)
        callback()

    def getProgress(self):
        if self.progress is not None:
            return max(0, min(self.progress, 100))
        return 0
        
    def LoadImages(self):
        tilesheet = pygame.image.load('data/Assets/Terrain/Terrain (16x16).png').convert_alpha()
        green_grass = GameManager.GetTerrainImages(tilesheet, 96, 0, 16)
        pink_grass = GameManager.GetTerrainImages(tilesheet, 96, 64, 16)
        orange_grass = GameManager.GetTerrainImages(tilesheet, 96, 128, 16)


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

    # Compile images
        images = {
            'green_grass': extract_tiles(green_grass),
            'orange_grass': extract_tiles(orange_grass),
            'pink_grass': extract_tiles(pink_grass),
            'empty' : {(0,0): None} 
        }
        return images


    def GetTerrainImages(tilesheet, x, y, size):
        return pygame.Surface.subsurface(tilesheet, pygame.Rect(x, y, size * 3, size * 3))

    def GetObjects(self):
        data = {}

        def getFruits():
            data = {}
            fruit_names = os.listdir('data\Assets\Objects\Fruits')
            collected_tilesheet = pygame.image.load(f'data\Assets\Objects\Fruits\Collected.png').convert_alpha()
            for fruit in fruit_names:
                fruit_type = fruit.replace('.png', '')
                tilesheet = pygame.image.load(f'data\Assets\Objects\Fruits\{fruit_type}.png').convert_alpha()            
                data[fruit_type] = {
                    'class' : Fruit,
                    'default_frames' : self.GetFrames(tilesheet, 32, 32, width_pad= 4, height_pad= 4),
                    'collected_frames': self.GetFrames(collected_tilesheet, 32, 32, width_pad= 4, height_pad= 4),
                    'standstill' : None, 
                    'scale' : 1,
                    'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE],
                    'offset' : Vector2(0,0),
                    'categories' : Collision_Types.COLLECTABLE,
                    'mask' : Collision_Types.collide_with([Collision_Types.PLAYER]),
                    'mass' : 1,
                    'radius' : lambda : GameManager.TILE_SIZE,
                    'moment' : lambda obj : pymunk.moment_for_circle(obj.mass, 0, obj.radius),
                    'shape' : lambda obj: pymunk.Circle(obj.body, obj.radius),
                    'body_type': pymunk.Body.STATIC,
                    'collision_type' : CTYPES.FRUIT
                    }
                data[fruit_type]['standstill'] = data[fruit_type]['default_frames'][0]
            return data
        
        def getFire():
            data = {}
            hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Fire/Hit (16x32).png').convert_alpha()
            off_sheet = pygame.image.load('data/Assets/Objects/Traps/Fire/Off.png').convert_alpha()
            on_sheet = pygame.image.load('data/Assets/Objects/Traps/Fire/On (16x32).png').convert_alpha()

            data['Fire'] = {
                'class' : Fire,
                'activate_frames' : self.GetFrames(hit_sheet, 16, 32),
                'deactivate_frames' : self.GetFrames(hit_sheet, 16, 32),
                'on_frames' : self.GetFrames(on_sheet, 16, 32),
                'off_frames' : off_sheet,
                'scale' : 1,
                'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE * 2 if GameManager.TILE_SIZE is not None else 0],
                'offset' : Vector2(0, -GameManager.TILE_SIZE/2 if GameManager.TILE_SIZE is not None else 0),
                'standstill' : off_sheet,
                'categories' : Collision_Types.ENEMIES,
                'mask' : Collision_Types.collide_with([Collision_Types.PLAYER, Collision_Types.ENEMIES, Collision_Types.TERRAIN, Collision_Types.PLATFORM]),
                'mass' : 10,
                'radius' : lambda : 1,
                'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                'body_type': pymunk.Body.DYNAMIC,
                'collision_type' : CTYPES.FIRE
            }
           
            return data
        
        def getSpike():
            data = {}
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Spikes/Idle.png').convert_alpha()

            data['Spike'] = {
                'class' : Spike,
                'idle_frames' : idle_sheet,
                'scale' : 1,
                'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE],
                'offset' : Vector2(0,0),
                'standstill' : idle_sheet,
                'categories' : Collision_Types.ENEMIES,
                'mask' : Collision_Types.collide_with([Collision_Types.PLAYER, Collision_Types.ENEMIES,Collision_Types.TERRAIN ]),
                'mass' : 100,
                'radius' : lambda : 1,
                'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                'body_type': pymunk.Body.STATIC,
                'collision_type' : CTYPES.SPIKE
            }
            return data
        
        def getRockHead():
            data = {}
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Idle.png').convert_alpha()
            bottom_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Bottom Hit (42x42).png').convert_alpha()
            top_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Top Hit (42x42).png').convert_alpha()
            right_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Right Hit (42x42).png').convert_alpha()
            left_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Left Hit (42x42).png').convert_alpha()
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Idle.png').convert_alpha()
            blink_sheet = pygame.image.load('data/Assets/Objects/Traps/Rock Head/Blink (42x42).png').convert_alpha()

            data['RockHead'] = {
                'class' : RockHead,
                'idle_frames' : [idle_sheet],
                'bottom_hit_frames' : self.GetFrames(bottom_hit_sheet, 42, 42),
                'top_hit_frames' : self.GetFrames(top_hit_sheet, 42, 42),
                'left_hit_frames' : self.GetFrames(left_hit_sheet, 42, 42),
                'right_hit_frames' : self.GetFrames(right_hit_sheet, 42, 42),
                'blink_frames' : self.GetFrames(blink_sheet, 42, 42),
                'scale' : 2.5,
                'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE],
                'offset' : Vector2(0,0),
                'standstill' : idle_sheet,
                'categories' : Collision_Types.ENEMIES,
                'mask' : Collision_Types.collide_with([Collision_Types.PLAYER, Collision_Types.ENEMIES, Collision_Types.TERRAIN]),
                'mass' : 100,
                'radius' : lambda : 1,
                'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                'body_type': pymunk.Body.KINEMATIC,
                'collision_type' : CTYPES.ROCKHEAD
            }
            

            return data

        def getSpikeHead():
            data = {}
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Idle.png').convert_alpha()
            bottom_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Bottom Hit (54x52).png').convert_alpha()
            top_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Top Hit (54x52).png').convert_alpha()
            right_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Right Hit (54x52).png').convert_alpha()
            left_hit_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Left Hit (54x52).png').convert_alpha()
            idle_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Idle.png').convert_alpha()
            blink_sheet = pygame.image.load('data/Assets/Objects/Traps/Spike Head/Blink (54x52).png').convert_alpha()

            data['SpikeHead'] = {
                'class' : RockHead,
                'idle_frames' : [idle_sheet],
                'bottom_hit_frames' : self.GetFrames(bottom_hit_sheet, 54, 52),
                'top_hit_frames' : self.GetFrames(top_hit_sheet, 54, 52),
                'left_hit_frames' : self.GetFrames(left_hit_sheet, 54, 52),
                'right_hit_frames' : self.GetFrames(right_hit_sheet, 54, 52),
                'blink_frames' : self.GetFrames(blink_sheet, 54, 52),
                'scale' : 3,
                'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE],
                'offset' : Vector2(0,0),
                'standstill' : idle_sheet,
                'categories' : Collision_Types.ENEMIES,
                'mask' : Collision_Types.collide_with([Collision_Types.PLAYER, Collision_Types.ENEMIES, Collision_Types.TERRAIN]),
                'mass' : 100,
                'radius' : lambda : 1,
                'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                'body_type': pymunk.Body.KINEMATIC,
                'collision_type' : CTYPES.ROCKHEAD
            }
            return data
       
        def getSaw():
            data = {}
            off_sheet = pygame.image.load('data/Assets/Objects/Traps/Saw/Off.png').convert_alpha()
            on_sheet = pygame.image.load('data/Assets/Objects/Traps/Saw/On (38x38).png').convert_alpha()
            data['Saw'] = {
                'class' : Saw,
                'on_frames' : self.GetFrames(on_sheet, 38, 38),
                'off_frames' : [off_sheet],
                'scale' : 3,
                'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE],
                'offset' : Vector2(0,0),
                'standstill' : off_sheet,
                'categories' : Collision_Types.ENEMIES,
                'mask' : Collision_Types.collide_with([Collision_Types.PLAYER, Collision_Types.ENEMIES, Collision_Types.TERRAIN]),
                'mass' : 100,
                'radius' : lambda : 1,
                'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                'body_type': pymunk.Body.KINEMATIC,
                'collision_type' : CTYPES.SAW
            }
            return data

        def getLiquids():
            data = {}
            standstill = pygame.Surface((5,5)).convert_alpha()
            data['Water'] = {
                'class' : Liquid,
                'color' : (130, 180, 235),
                'scale' : 1,
                'size' : lambda : [GameManager.TILE_SIZE/5, GameManager.TILE_SIZE/5],
                'offset' : Vector2(0,0),
                'standstill' : standstill,
                'categories' : Collision_Types.PARTICLES,
                'mask' : Collision_Types.collide_with([Collision_Types.TERRAIN]),
                'mass' : 100,
                'radius' : lambda : 1,
                'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                'body_type': pymunk.Body.KINEMATIC,
                'collision_type' : CTYPES.LIQUID
            }
            standstill.fill(data['Water']['color'])
            return data
        
        def getParticles():
            data = {}
            standstill = pygame.Surface((32,32)).convert_alpha()
            data['Particle'] = {
                'class' : Particle,
                'color' : (135,206,235),
                'scale' : 1,
                'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE],
                'offset' : Vector2(0,0),
                'standstill' : standstill,
                'categories' : Collision_Types.PARTICLES,
                'mask' : Collision_Types.collide_with([Collision_Types.TERRAIN]),
                'mass' : 100,
                'radius' : lambda : 1,
                'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                'body_type': pymunk.Body.KINEMATIC,
                'collision_type' : CTYPES.PARTICLE
            }
            standstill.fill(data['Particle']['color'])
            return data

        def getSpring():
            data = {}
            standstill = pygame.image.load('data/Assets/Objects/Traps/Trampoline/Idle.png').convert_alpha()
            jump_sheet = pygame.image.load('data/Assets/Objects/Traps/Trampoline/Jump (28x28).png').convert_alpha()
            data['Spring'] = {
                'class' : Spring,
                'scale' : 1,
                'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE],
                'offset' : Vector2(0,0),
                'standstill' : standstill,
                'idle_frames' : [standstill],
                'activate_frames' : self.GetFrames(jump_sheet, 28, 28),
                'deactivate_frames' : self.GetFrames(jump_sheet, 28, 28, reverse = True),
                'categories' : Collision_Types.PLATFORM,
                'mask' : Collision_Types.collide_with([Collision_Types.TERRAIN, Collision_Types.ENEMIES]),
                'mass' : 100,
                'radius' : lambda : 1,
                'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                'body_type': pymunk.Body.KINEMATIC,
                'collision_type' : CTYPES.SPRING
                }
            data['Spring']['on_frames'] = [data['Spring']['activate_frames'][len(data['Spring']['activate_frames']) - 1]]

            return data

        def getPlatforms():
            data = {}
            for platform in ['Brown', 'Grey']:
                on_frames = pygame.image.load(f'data/Assets/Objects/Traps/Platforms/{platform} Off.png').convert_alpha()
                off_frames = pygame.image.load(f'data/Assets/Objects/Traps/Platforms/{platform} Off.png').convert_alpha()
                data[platform] = {
                    'class' : PlatForm,
                    'scale' : 2,
                    'size' : lambda : [GameManager.TILE_SIZE, GameManager.TILE_SIZE/4],
                    'offset' : Vector2(0,0),
                    'standstill' : off_frames,
                    'on_frames' : self.GetFrames(on_frames, 32, 8),
                    'off_frames' : self.GetFrames(off_frames, 32, 8),
                    'categories' : Collision_Types.PLATFORM,
                    'mask' : Collision_Types.collide_with([Collision_Types.ENEMIES]),
                    'mass' : 100,
                    'radius' : lambda : 5,
                    'moment' : lambda obj : pymunk.moment_for_box(obj.mass, obj.rect.size),
                    'shape' : lambda obj: pymunk.Poly.create_box(obj.body, obj.rect.size, obj.radius),
                    'body_type': pymunk.Body.KINEMATIC,
                    'collision_type' : CTYPES.PLATFORM
                    }
            return data
        data.update(**getFruits())
        data.update(**getFire())
        data.update(**getSpike())
        data.update(**getRockHead())
        data.update(**getSpikeHead())
        data.update(**getSaw())
        data.update(**getLiquids())
        data.update(**getParticles())
        data.update(**getSpring())
        data.update(**getPlatforms())
        return data

    def create_collision_handlers(self, id, cls, type_a, type_b):
        handlers= []
        for i in range(cls.ID):
            handler = self.space.add_collision_handler(type_a | id, type_b | i)
            handlers.append(handler)

        return handlers
        
    
    def GetTiles(self):
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

        data = {}
        i = 0
        for key, val in self.TILE_TYPES.items():
            try:
                data[key] = {"full": GameManager.GetTerrainImages(tilesheet, 96, i, 16),
                             'categories': Collision_Types.TERRAIN, 'mask' : Collision_Types.collide_with([Collision_Types.ENEMIES, Collision_Types.PLAYER, Collision_Types.PARTICLES]), 'friction' :0.25}
                data[key]['split'] = extract_tiles(data[key]['full'])
                i+= 64
            except:
                break
        data['sand'] = {"full": GameManager.GetTerrainImages(tilesheet2, 0, 0, 16),
                        'categories': Collision_Types.TERRAIN, 'mask' : Collision_Types.collide_with([Collision_Types.ENEMIES, Collision_Types.PLAYER, Collision_Types.PARTICLES]), 'friction' :0.25}
        data['sand']['split'] = extract_tiles(data['sand']['full'])
        data['mud'] = {"full": GameManager.GetTerrainImages(tilesheet2, 64, 0, 16),
                       'categories': Collision_Types.TERRAIN, 'mask' : Collision_Types.collide_with([Collision_Types.ENEMIES, Collision_Types.PLAYER, Collision_Types.PARTICLES]), 'friction' :0.25}
        data['mud']['split'] = extract_tiles(data['mud']['full'])
        data['ice'] = {"full": GameManager.GetTerrainImages(tilesheet2, 128, 0, 16),
                        'categories': Collision_Types.TERRAIN, 'mask' : Collision_Types.collide_with([Collision_Types.ENEMIES, Collision_Types.PLAYER, Collision_Types.PARTICLES]), 'friction' :0.25}
        data['ice']['split'] = extract_tiles(data['ice']['full'])
        data['water'] = {'full' : watersheet,
                         'categories': Collision_Types.TERRAIN, 'mask' : Collision_Types.collide_with([Collision_Types.ENEMIES, Collision_Types.PLAYER, Collision_Types.PARTICLES]), 'friction' :0.25}
        #data['water']['full'].fill((130,163,255))
        data['water']['split'] = extract_tiles(data['water']['full'])
        data['empty'] = {'full' : None, 'split' : None, 
                         'categories': Collision_Types.NOTHING, 'mask' : Collision_Types.NOTHING, 'friction' :0.25}
        return data

    def GetFrames(self, tilesheet : pygame.Surface, width, height,
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

    def SaveLevel(self):
        lock = threading.Lock()
        with lock:
            if not self.saving:
                print('intitiating thread worked')
                self.saving = True     
                saving_thread = threading.Thread(target= lambda: self.InitiateSave(self.FinshedSaving))
                saving_thread.start()
        
        
    def InitiateSave(self, callback):
        print('In Thread')
        directory = 'data/Levels/'
        terrain_path = os.path.join(directory, self.levelName, 'terrain.json')
        objects_path = os.path.join(directory, self.levelName, 'objects.json')  
        settings_path = os.path.join(directory, self.levelName, 'settings.json')
        objects_file_size = len(self.gameObjects)
        terrain_file_size = self.WORLD_WIDTH * self.WORLD_HEIGHT * self.LAYERS
        settings_file_size = len(self.settings['saved_settings'])
        total_file_size = terrain_file_size + objects_file_size + settings_file_size
        self.progress = 0
        progress = 0

        for _ in self.SaveSettings(settings_path):
            progress += 1/total_file_size
            self.progress = int(progress * 100)

        for _ in self.SaveTerrain(terrain_path):
            progress += 1/total_file_size
            self.progress = int(progress * 100)
        for _ in self.SaveObjects(objects_path):
            progress += 1/total_file_size
            self.progress = int(progress * 100)
        
        print(self.progress)
        if callable(callback):
            callback()


    def FinshedSaving(self):
        self.saving = False
        print('callback worked')

    def SaveTerrain(self, terrain_path):
        cache = {
            "width": self.WORLD_WIDTH,
            "height": self.WORLD_HEIGHT,
            "tileSize": self.TILE_SIZE,
            "layers": self.LAYERS,
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
                        tile_data = self.terrain.get((x, y)).get(layer).ToDict()
                        if layer < cache["layers"] - 1:
                            file.write(f"  \"{layer}\": {json.dumps(tile_data)},\n")
                        else:
                            file.write(f"  \"{layer}\": {json.dumps(tile_data)}\n")
                        yield
                    file.write("}")
            file.write("\n}\n}")
            yield

    def SaveObjects(self, object_path):
        with open(object_path, 'w') as file:
            file.write("{\n")

            for index, game_object in enumerate(self.gameObjects):
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
                    yield
            file.write("}")

    def SaveSettings(self, settings_path):
        with open(settings_path, 'w') as file:
            file.write("{")
            for index, (key, value) in enumerate(self.settings['saved_settings'].items()):
                if index > 0:
                    file.write(f",  \"{key}\": {value}")
                else:
                    file.write(f"  \"{key}\": {value}")
                yield      
            file.write("}")

    def createLevel(self, data):
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
            json.dump({'world_brightness' : 1}, file)
        

def createFile():
    os.makedirs("data/Levels", exist_ok=True)
    data = {
        "cache": {
            "width": 100,
            "height": 200,
            "tileSize": 20,
            'layers' : 3
        },
        "tiles": {}
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

    with open('data/Levels/Level1/terrain.json', 'w') as file:
        json.dump(data, file, indent=1)
