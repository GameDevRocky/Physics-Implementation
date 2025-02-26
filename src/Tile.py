import pygame
import pymunk

class Tile:

    def __init__(self, pos : pygame.Vector2, type, coll, variation, id, layer, level) -> None:
        from levels import Level
        self.level : Level = level 
        self.pos = pos + pygame.Vector2((self.level.tile_size, self.level.tile_size))/2
        self.variation = variation
        self.coll = coll
        self.type = type
        self.id = id
        self.img = self.level.manager.assets.tile_assets.get(self.type)
        if self.img:
            self.img = self.level.manager.assets.tile_assets.get(self.type).get(tuple(self.variation))
        
        self.layer = layer
        self.rect = pygame.Rect(self.pos,(self.level.tile_size, self.level.tile_size))
        self.rect.center= self.pos
        if self.img:
            self.img = pygame.transform.smoothscale(self.img, (self.level.tile_size, self.level.tile_size))
        cache = self.level.manager.assets.tile_assets[self.type]
        self.mass = cache['mass']
        self.body = pymunk.Body(100, pymunk.moment_for_box(self.mass, self.rect.size) ,pymunk.Body.STATIC)
        self.body.position = (self.pos.x, self.pos.y)
        self.shape = pymunk.Poly.create_box(self.body, self.rect.size, radius= 0.5)
        self.shape.friction = cache['friction']
        self.shape.elasticity = cache['elasticity']
        if self.type == 'empty':
            self.shape.sensor = True
        else:
            self.shape.sensor = False
          

    def SetTo(self, type: str, variation):
        self.type = type

        cache = self.level.manager.assets.tile_assets[self.type]
        self.mass = cache['mass']
        self.shape.friction = cache['friction']
        self.shape.elasticity = cache['elasticity']
        if self.type == 'empty':
            self.shape.sensor = True
        else:
            self.shape.sensor = False
        values = self.level.manager.assets.tile_assets.get(self.type)
        if values:
            terrain = values.get('split')
            if terrain:
                img = terrain.get(variation)
                if img:
                    self.img = pygame.transform.smoothscale(img, (self.level.tile_size, self.level.tile_size))
                else:
                    self.img = None
            else:
                self.img = None
        else:
            self.img = None

    def ToDict(self):
        data = {'coll' : self.coll,
                'type' : self.type,
                'variation' : self.variation
                }
        return data


