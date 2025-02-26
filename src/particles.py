import math
from pygame.color import Color
import pygame
from random import *
from objects import GameObject
from pygame.math import Vector2
from lightsource import LightSource
import pymunk
class Particle(GameObject):
    def __init__(self, pos: Vector2 = ..., orientation: Vector2 = ..., 
                 type: str = '', layer: int = 0, level=None) -> None:
        super().__init__(pos, orientation, type, layer, level)
        self.canCover = True

    def idle(self, deltatime):
        pass

    def ToDict(self):
        return None
    
    def remove(self):
        self.active = False

class DefaultParticle(Particle):
    def __init__(self, pos: Vector2 = ..., orientation: Vector2 = ..., 
                 type: str = '', layer: int = 0, level=None,
                 velocity : Vector2 = Vector2(0,0), color : Color = Color(255,255,255,255)) -> None:
        super().__init__(pos, orientation, type, layer, level)
        self.tick = 0
        self.color = color
        self.rect = self.img.get_rect()
        self.alpha = randint(100, 255)
        self.frequency = randint(5,10)
        self.fade_speed = randint(5,10)/1000
        self.body.apply_impulse_at_world_point(tuple(velocity), self.body.position)

    def idle(self, deltatime):
        self.tick += 1
        self.radius -= self.fade_speed
        self.body.velocity *= 0.99
        super().update(deltatime)
        if self.radius <= 0.1:
            self.remove()

    def update(self, deltatime):
        super().update(deltatime)
    
    def ToDict(self):
        return None
        
class Spark(Particle, LightSource):
    def __init__(self, pos: Vector2 = ..., orientation: Vector2 = ..., type: str = '',
                  layer: int = 0, level=None, velocity: Vector2 = Vector2(0, 0), 
                  color: Color = Color(255, 255, 255, 255)) -> None:
        super().__init__(pos, orientation, type, layer, level)
        LightSource.__init__(self, self.pos)
        self.strength = 1
        self.light_radius = self.level.tile_size/10
        self.light_strength = 1
        self.frequency = randint(5,10)
        self.fade_speed = randint(5,10)/1000
        self.float_speed = randint(2,7)/10
        self.body.velocity = tuple(velocity)



    def idle(self, deltatime):
        self.tick += 1
        self.light_radius -= self.fade_speed
        self.body.velocity *= 0.99
        self.updatePos(self.pos, self.level.camera)
        if self.light_radius <= 0.1:
            self.remove()

        Particle.update(self, deltatime)

class Rain(DefaultParticle):
    def __init__(self, pos = ..., orientation = ..., type = '', layer = 0, level=None, velocity = Vector2(0, 0), color = Color(255, 255, 255, 255)):
        super().__init__(pos, orientation, type, layer, level, velocity, color)
        self.body.apply_impulse_at_world_point(tuple(velocity), self.body.position)
        self.shape.sensor = True
    

    def idle(self, deltatime):
        
        self.tick += 1

        if self.tick > 200:
            self.active = False

        super().update(deltatime)

        pass
