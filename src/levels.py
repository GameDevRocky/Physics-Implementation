import time
import pygame
import pymunk
import os
import json
import math
import logging
import threading
from pygame.math import Vector2
from Tile import Tile
from objects import*
from Camera import Camera
from Input import InputHandler
from types import GeneratorType
from array import array
from collision_categories import CTYPES
from concurrent.futures import ThreadPoolExecutor

class Level:
    SIMULATION_STEPS = 10
    GRAVITY = 200

    def __init__(self, manager):
        from managers import EditorManager
        self.manager: EditorManager = manager
        self.input: InputHandler = self.manager.input
        self.world_width = None
        self.world_height = None
        self.tile_size = None
        self.layers = None
        self.name = None
        self.camera = Camera(self, self.input)
        self.terrain : dict = {}
        self.game_objects: list = []
        self.spaces= []
        self.bounding_rect = None
        self.settings = {'zoom' : 0.5}
        self.screens = []
        self.loaded_percentage = 0
        self.saved_percentage = 0
        self.current_layer = 0
        self.current_background = 0
        self.active = False
        self.optimized_view = {}
        self.on_screen_tiles = []
        self.on_screen_objects = []
        self.generator_tasks = {}
        self.removed_objects = set()
        self.queued_objects = set()
        self.shader_data = {}
        self.liquid_bodies = set()
        self.lightsources = set()
        self.time_elapsed = 0 
        self.debug = False
        print(CTYPES.__dict__)

    
    def initialize(self):
        self.active = True
        self.camera.pos = Vector2(0,0)
        self.camera.velocity = Vector2(0,0)
        self.camera.input = self.input
        self.optomized_view = self.get_optomized_view()
        for space in self.spaces:
            space.gravity = (0, self.GRAVITY)
        for obj in self.game_objects:
            obj.initialize()
    
    def clear_screens(self):
        for screen in self.screens:
            screen.fill((0,0,0,0))

    def update(self, deltatime):
        if self.active:
            self.time_elapsed += deltatime
            self.clear_screens()
            self.optomized_view = self.get_optomized_view()
            self.on_screen_tiles = self.get_onscreen_tiles()
            self.on_screen_objects.clear()
            self.update_generator_tasks()
            self.camera.update(deltatime)
            self.update_settings()
            self.add_objects_to_space()
            self.add_objects_to_game_objects()
            self.update_objects(deltatime)
            self.remove_objects_from_space()
            self.update_spaces(deltatime)
            self.remove_objects_from_game_objects()
            self.remove_objects_from_queue()
            self.update_shader_data()
            self.render()
    
    def update_settings(self):
        self.settings['zoom'] = self.camera.zoom

    def update_generator_tasks(self) -> None:
        for key, task in list(self.generator_tasks.items()):
            try:
                returned_task = next(task)
                if isinstance(returned_task, GeneratorType):
                    self.generator_tasks[key] = returned_task
            except StopIteration:
                self.generator_tasks.pop(key, None)
            except Exception as e:
                logging.error(f"Error in generator task {key}: {e}")

    def update_spaces(self, deltatime):
        
        for space in self.spaces:
            for _ in range(self.SIMULATION_STEPS):
                space.step(deltatime/self.SIMULATION_STEPS)

    def update_objects(self, deltatime):
        from objects import Liquid

        for obj in self.game_objects:
            if isinstance(obj, Liquid):
                self.liquid_bodies.add(obj)
    
            if obj.rect.colliderect(self.camera.rect):
                self.on_screen_objects.append(obj)
                if isinstance(obj, LightSource):
                    self.lightsources.add(obj)
            step_time = deltatime / self.SIMULATION_STEPS
            if self.time_elapsed % step_time < step_time:
                obj.idle(deltatime)
            if not obj.active:
                self.removed_objects.add(obj)

    def add_objects_to_space(self) -> None:
        for obj in self.queued_objects:
            if obj.body not in self.spaces[obj.layer].bodies:
                self.spaces[obj.layer].add(obj.body)
            if obj.shape not in self.spaces[obj.layer].shapes:
                self.spaces[obj.layer].add(obj.shape)
            if hasattr(obj, 'constraint'): 
                if obj.constraint not in self.spaces[obj.layer].constraints:
                    self.spaces[obj.layer].add(obj.constraint)         

    def update_shader_data(self):
        self.shader_data['resolution'] = array('f', self.manager.app.window.size)
        self.update_liquid_shader_data()
        self.update_lightsources_shader_data()
        self.update_background_shader_data()

    def update_liquid_shader_data(self):
        data = [[0.0] * 8] * 10
        count = 0
        for body in self.liquid_bodies:
            if count < 10:
                coords = [body.body_rect.left - self.camera.pos.x,body.body_rect.top - self.camera.pos.y, body.body_rect.w , body.body_rect.h]
                data_ = [int(body.texture_index), 0, 0, 0]
                data[count] = coords + data_
                count+= 1
                
        self.shader_data['liquid_data'] = array('f', [data_ for mat in data for data_ in mat])
        self.shader_data['liquid_textures'] = 20
        self.shader_data['liquid_color'] = array('f', [1, 0, 1, 1])
        self.shader_data['ld_length'] = count + 1
        self.shader_data['tile_size'] = self.tile_size

    def update_lightsources_shader_data(self):
        data = [[0.0] * 8] * 100
        index = 0
        for index, lightsource in enumerate(self.lightsources):
            if index < 100:
                data[index] = lightsource.toData()
            else:
                break
                
        self.shader_data['lightsource_data'] = array('f', [data for coordinates in data for data in coordinates])
        self.shader_data['ls_length'] = index + 1
        self.shader_data['camera_pos'] = array('f', [self.camera.pos.x, self.camera.pos.y])

    def update_background_shader_data(self):
        self.shader_data['background_index'] = self.current_background
        self.shader_data['background_textures'] = 10

    def add_objects_to_game_objects(self) -> None:
        for obj in self.queued_objects:
            if obj.body in self.spaces[obj.layer].bodies and obj.shape in self.spaces[obj.layer].shapes:
                self.game_objects.append(obj)

    def init_remove_all_objects(self):
        thread = threading.Thread(target= self.remove_all_objects)
        thread.start()   

    def init_remove_all_tiles(self):
        thread = threading.Thread(target= self.remove_all_tiles)
        thread.start()      
    
    def remove_all_objects(self):
        def remove_objects():
            copied_game_objects = self.game_objects.copy()
            for obj in copied_game_objects:
                self.pop_object(obj)
                yield

        run = True
        task = remove_objects()
        count = 0
        while run:
            try:
                next(task)
            except:
                
                if len(self.game_objects) == 0:
                    run = False

                else:
                    count+=1 
                    task = remove_objects() 
                    print(count)
            time.sleep(0.01)    


    def remove_all_tiles(self):
        print(self.terrain.items())
        def remove_tiles():
            for x in range(self.world_width):
                for y in range(self.world_height):
                    for l in range(self.layers):
                        self.terrain.get((x,y)).get(l).SetTo('empty', None)
                yield

        run = True
        task = remove_tiles()
        while run:
            try:
                next(task)
            except:
                run = False
            time.sleep(0.01)
        

    def remove_objects_from_space(self) -> None:
        for obj in self.removed_objects:
            self.spaces[obj.layer].remove(obj.body, obj.shape)
            if hasattr(obj, 'constraint'):
                self.spaces[obj.layer].remove(obj.constraint)


    def remove_objects_from_game_objects(self) -> None:
        removed_objects = []
        for obj in self.removed_objects:
            if obj.body not in self.spaces[obj.layer].bodies and obj.shape not in self.spaces[obj.layer].shapes:
                self.game_objects.remove(obj)
                if obj in self.liquid_bodies:
                    self.liquid_bodies.remove(obj)
                if obj in self.lightsources:
                    self.lightsources.remove(obj)
                removed_objects.append(obj)

        self.removed_objects.difference_update(removed_objects)

    def remove_objects_from_queue(self) -> None:
        self.queued_objects.difference_update(self.game_objects)

    def add_object_to_queue(self, obj) -> None:
        self.queued_objects.add(obj)
        
    def render(self):
        self.render_tiles()
        self.render_objects()
        self.render_liquid_bodies()
        self.render_editor()
        self.render_bounding_rect()

    def render_tiles(self):
        for tile in self.on_screen_tiles:
            if tile.img:
                self.screens[tile.layer].blit(tile.img, tile.rect.topleft - self.camera.pos)

    def render_objects(self):
        from objects import Liquid, Pendulum
        for obj in self.on_screen_objects:
            if isinstance(obj, Liquid):
                continue
            screen = self.screens[obj.layer]
            if obj.img:
                screen.blit(obj.img, obj.rect.topleft - self.camera.pos)
            
                if self.manager.editor.selector_rect.contains(obj.rect):
                    rect = obj.rect.copy()
                    rect.center -= self.camera.pos
                    pygame.gfxdraw.rectangle(screen, rect, (255,255,255))
                if isinstance(obj, Pendulum):
                    pygame.draw.line(screen, (255,255,255), obj.anchor.body.position - self.camera.pos, obj.pos - self.camera.pos)

    def render_liquid_bodies(self):
        from objects import Liquid
        from particles import Particle
        for obj in self.liquid_bodies:
            screen = self.screens[obj.layer]
            if obj.img:
                for on_screen_obj in self.on_screen_objects:
                    if isinstance(on_screen_obj, Liquid):
                        continue
                    if isinstance(on_screen_obj, Particle):
                        continue
                    if obj.rect.colliderect(on_screen_obj.rect):
                        img_copy = pygame.transform.solid_overlay(on_screen_obj.img.copy(), (255,0,0), keep_alpha= False)
                        surf = img_copy.copy()
                        surf.fill((255,255,255))
                        surf.blit(img_copy, (0,0))

                        rect = obj.img.get_rect()
                        obj.img.blit(surf, rect.center + (on_screen_obj.rect.topleft - Vector2(obj.rect.center)), special_flags= pygame.BLEND_MULT)
                for tile in obj.surrounding_terrain:
                    if tile.type != 'empty':
                        img_copy = tile.img.copy()
                        img_copy.fill((0,255,0, 0))
                        rect = obj.img.get_rect()
                        obj.img.blit(img_copy, rect.center + (tile.rect.topleft - Vector2(obj.rect.center)),special_flags= pygame.BLEND_RGBA_MULT)

                screen.blit(obj.img, obj.rect.topleft - self.camera.pos)
                
    def render_editor(self):
        screen : pygame.Surface = self.screens[self.manager.editor.layer]
        if self.manager.editor.img:
            screen.blit(self.manager.editor.img, self.manager.editor.rect.topleft - self.camera.pos)
        pygame.gfxdraw.rectangle(screen, self.manager.editor.on_screen_rect, (255,255,255))
        pygame.gfxdraw.rectangle(screen, self.manager.editor.on_screen_selector_rect, (255,255,255))

    def render_bounding_rect(self):
        screen = self.screens[self.current_layer]
        rect = self.bounding_rect.copy()
        rect.center -= self.camera.pos
        pygame.gfxdraw.rectangle(screen, rect, (255,255,255))

    def get_optomized_view(self):
        return {
        'left' : int(math.floor(self.camera.pos.x / self.tile_size) - self.tile_size),
        'top': int(math.floor(self.camera.pos.y / self.tile_size) - self.tile_size),
        'right' : int(math.ceil(self.camera.pos.x / self.tile_size + self.manager.app.SCREEN_WIDTH / self.tile_size) + self.tile_size),
        'bottom' : int(math.ceil(self.camera.pos.y / self.tile_size + self.manager.app.SCREEN_HEIGHT / self.tile_size) + self.tile_size)
        }

    def auto_tile(self):
        tiles = self.get_onscreen_tiles()
        for tile in tiles:
            self.check_neighboring_tiles(tile)

    def check_neighboring_tiles(self, tile : Tile):
    
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

            if  tuple(list) in self.manager.assets.auto_tile_map:
                tile.SetTo(tile.type, self.manager.assets.auto_tile_map[tuple(list)])

    def pop_object(self, obj):
        from objects import GameObject
        print(obj)
        if isinstance(obj, GameObject):
            obj.active = False

    def get_onscreen_tiles(self):
        tiles = []
        count = 0
        for x in range(self.optomized_view['left'], self.optomized_view['right']):
            for y in range(self.optomized_view['top'], self.optomized_view['bottom']):
                for layer in range(self.layers):
                    row = self.terrain.get((x,y))
                    if row:
                        tile = row.get(layer)
                        if tile:
                            tiles.append(tile)
        return tiles
    
    def generate_rain(self):
        from particles import Rain
        rain = Rain(pos= Vector2(randint(int(self.camera.pos.x), int(self.camera.pos.x + self.manager.app.SCREEN_WIDTH)), self.camera.pos.y),
                   orientation= Vector2(0,1), layer= randint(0, self.layers - 1), level= self, velocity= Vector2(0, -50), color= (120, 130, 230, 150),
                   type= 'Rain')
        self.add_object_to_queue(rain)

    def add_collision_handlers(self):
        from objects import Liquid, PlatForm
        for space in self.spaces:
            self.add_handlers(space, CTYPES.liquid, [CTYPES.enemy, CTYPES.collectable, CTYPES.platform],
                                        begin = Liquid.splash)
            self.add_handlers(space, CTYPES.platform,[CTYPES.enemy, CTYPES.collectable], post_solve= PlatForm.add_movement)

    def add_handlers(self, space : pymunk.Space, type_a, types : list, begin = None, pre_solve = None, post_solve = None, separate = None):
        for coll_type in types:
            handler = space.add_collision_handler(type_a, coll_type)
            if begin:
                handler.begin = begin
            if pre_solve:
                handler.pre_solve = pre_solve
            if post_solve:
                handler.post_solve = post_solve
            if separate:
                handler.separate = separate

    def close(self):
        self.active = False