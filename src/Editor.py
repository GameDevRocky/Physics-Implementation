import pygame
from pygame.math import Vector2
import math
from Input import EditorActions
from Tile import Tile
from objects import *
from particles import *

class Editor:
    def __init__(self, manager) -> None:
        from managers import EditorManager
        self.manager: EditorManager = manager
        self.active = False
        self.level = None
        self.pos = Vector2(0, 0)
        self.rawPos = Vector2(0, 0)
        self.snappedPos = Vector2(0, 0)
        self.input: EditorActions = self.manager.input.EditorAction
        self.rect = pygame.Rect(0, 0, 1, 1)
        self.on_screen_rect = pygame.Rect(0, 0, 1, 1)
        self.selector_rect = pygame.Rect(0, 0, 0, 0)
        self.on_screen_selector_rect = pygame.Rect(0, 0, 0, 0)
        self.selector_rect_start_point = Vector2(0, 0)
        self.layer = None
        self.edit_type = None
        self.type = None
        self.object_class = None
        self.object_args = None
        self.object_kwargs = {}
        self.object_offset = Vector2(0, 0)
        self.img = None
        self.paint_size = 1
        self.erasing = False
        self.just_erased = False
        self.orientation = Vector2(1, 0)

    def initialize(self, level: Level):
        self.level = level
        self.rect = pygame.Rect(self.pos.x, self.pos.y, self.level.tile_size, self.level.tile_size)
        self.reset_editor_state()

    def close(self):
        self.active = False
        self.level = None
        self.layer = None
        self.rect = pygame.Rect(0, 0, 1, 1)

    def reset_editor_state(self):
        self.edit_type = None
        self.type = None
        self.img = None
        self.layer = self.level.current_layer
        self.active = True

    def update(self, delta_time):
        if self.active:
            self.layer = self.level.current_layer
            self.update_positions()
            self.update_kwargs()
            self.erase_objects()
            self.update_image()
            self.process_editing()

    def update_positions(self):
        pos = Vector2(self.input.mouse)
        pos -= Vector2(self.manager.app.SCREEN_WIDTH, self.manager.app.SCREEN_HEIGHT) * 0.5
        pos /= self.level.camera.zoom
        pos += Vector2(self.manager.app.SCREEN_WIDTH, self.manager.app.SCREEN_HEIGHT) * 0.5

        self.rawPos = pos  + self.level.camera.pos
        self.pos = Vector2(math.floor(self.rawPos.x / self.level.tile_size) * self.level.tile_size,
            math.floor(self.rawPos.y / self.level.tile_size) * self.level.tile_size)
        self.snappedPos = Vector2(self.pos) + Vector2(self.level.tile_size, self.level.tile_size)/2
        self.rect.center = self.snappedPos
        self.update_on_screen_rect()

    def update_on_screen_rect(self):
        self.on_screen_rect = self.rect.copy()
        self.on_screen_rect.center -= self.level.camera.pos

    def update_image(self):
        if self.img:
            self.img.set_alpha(150 if not self.erasing else 0)

    def update_kwargs(self):
        self.object_kwargs = {
            'pos': self.snappedPos + self.object_offset,
            'orientation': self.orientation,
            'type': self.type,
            'layer': self.layer,
            'level': self.level,
        }

    def process_editing(self):
        match self.edit_type:
            case 'tile':
                self.edit_tiles()
            case 'object':
                self.edit_objects()
            case 'path':
                self.edit_paths()
            case 'liquid':
                self.edit_liquids()
            case _:
                pass

    def edit_tiles(self):
        rows = self.get_neighboring_rows()
        for row in rows:
            if row:
                tile = row.get(self.layer)
                if tile:
                    if self.input.erase and tile.type != 'empty':
                        self.level.pop_object(tile)
                        tile.SetTo('empty', None)
                    elif self.input.paint or self.input.pressed:
                        tile.SetTo(self.type, (0, 0))
        if self.input.autoTile:
            self.level.auto_tile()

    def get_neighboring_rows(self):
        rows = []
        tile_size = self.level.tile_size
        for x in range(-self.paint_size, self.paint_size + 1):
            for y in range(-self.paint_size, self.paint_size + 1):
                neighbor_pos = self.pos + Vector2(x * tile_size, y * tile_size)
                row = self.level.terrain.get(tuple(neighbor_pos / tile_size))
                rows.append(row)
        return rows

    def update_tile_image(self, type):
        tile_size = self.level.tile_size
        radius = self.paint_size * 2 + 1
        surf = pygame.Surface((radius * tile_size, radius * tile_size), pygame.SRCALPHA).convert_alpha()
        surf.set_alpha(175)
        values = self.manager.assets.tile_assets.get(type)
        self.object_offset = Vector2(0, 0)
        if values:
            terrain = values.get('split')
            if terrain:
                img = terrain[(0, 0)]
                if img:
                    img = pygame.transform.scale(img, (tile_size, tile_size))
                    for x in range(-self.paint_size, self.paint_size + 1):
                        for y in range(-self.paint_size, self.paint_size + 1):
                            px = (x + self.paint_size) * tile_size
                            py = (y + self.paint_size) * tile_size
                            surf.blit(img, (px, py))
                    self.img = surf
                    self.rect.size = surf.get_size()

    def edit_objects(self):
        if self.input.paint or self.input.pressed:
            if self.object_class:
                if self.check_colliding_objects():
                    kwargs = {
                        **self.object_kwargs, **self.object_args
                    }
                    object = self.object_class(**kwargs)
                    self.level.add_object_to_queue(object)

    def check_colliding_objects(self):
        colliding = self.rect.collideobjects([obj for obj in self.level.game_objects if obj.layer == self.layer and not obj.canCover])
        return not colliding

    def erase_objects(self):
        self.just_erased = False
        if self.edit_type == 'tile':
            self.selector_rect = pygame.Rect(0, 0, 0, 0)
            self.on_screen_selector_rect = pygame.Rect(0, 0, 0, 0)
            return
        elif self.input.erase_start:
            self.erasing = True
            self.selector_rect_start_point = Vector2(self.rawPos)
        if not self.input.erase and (self.edit_type != 'path' or self.edit_type != 'liquid'):
            pass
            #self.reset_erase_state()
        elif self.input.erase:
            self.render_selector_rect()
        if self.input.submit and self.erasing:
            self.just_erased = True
            self.remove_objects()
            self.reset_selector_rect()
            self.reset_erase_state()
            print('erasing')


    def reset_erase_state(self):
        self.selector_rect = pygame.Rect(0, 0, 0, 0)
        self.selector_rect_start_point = Vector2(0, 0)
        self.on_screen_selector_rect = pygame.Rect(0, 0, 0, 0)
        self.erasing = False

    def remove_objects(self):
        for obj in self.level.game_objects:
            if obj.layer == self.layer and self.selector_rect.contains(obj.rect):
                if obj.remove() is None:
                    self.level.pop_object(obj)
        self.selector_rect = pygame.Rect(0, 0, 0, 0)
        self.erasing = False

    def render_selector_rect(self):
        self.selector_rect = pygame.Rect(self.selector_rect_start_point, self.snappedPos - self.selector_rect_start_point)
        self.selector_rect.normalize()
        self.on_screen_selector_rect = self.selector_rect.copy()
        self.on_screen_selector_rect.center -= self.level.camera.pos

    def update_object_image(self, type):
        object_data = self.manager.assets.object_assets.get(type)
        if object_data:
            img = object_data.get('standstill')
            size = Vector2(object_data.get('size')(self.level))
            scale = object_data.get('scale')
            self.object_offset = object_data.get('offset')
            if callable(self.object_offset):
                self.object_offset = self.object_offset(self.level)
            if img:
                img = pygame.transform.smoothscale(img, size * scale)
                self.img = img
                self.rect.size = self.img.get_size()

    def edit_paths(self):
        if self.input.pressed and not self.erasing:
            self.selector_rect_start_point = Vector2(self.snappedPos)
        elif self.input.paint and not self.erasing:
            self.render_selector_rect()
        elif self.input.submit and not self.erasing and not self.just_erased:
            if self.check_colliding_objects():
                if self.object_class:
                    kwargs = {
                        **self.object_kwargs, **self.object_args
                    }
                    object = self.object_class(**kwargs)
                    self.level.add_object_to_queue(object)
                    self.reset_selector_rect()

    def edit_liquids(self):
        if self.input.pressed and not self.erasing:
            self.selector_rect_start_point = Vector2(self.snappedPos)
        elif self.input.paint and not self.erasing:
            self.render_selector_rect()

        elif self.input.submit and not self.erasing and not self.just_erased:
            if self.check_colliding_objects():
                print(self.input.submit)
                if self.object_class:
                    kwargs = {
                        **self.object_kwargs, **self.object_args
                    }
                    object = self.object_class(**kwargs)
                    print(object)
                    self.level.add_object_to_queue(object)
                    self.reset_selector_rect()

    def reset_selector_rect(self):
        self.selector_rect = pygame.Rect((0, 0), (0, 0))
        self.on_screen_selector_rect = pygame.Rect((0, 0), (0, 0))
