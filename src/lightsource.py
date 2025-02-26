from pygame.math import Vector2
from array import array
class LightSource:
    def __init__(self, pos : Vector2 = Vector2(0,0)) -> None:
        self.screen_pos = pos
        self.light_radius = 5
        self.color = [1,1,0.5]
        self.light_strength = 0.5
    
    def updatePos(self, real_pos, camera):
        self.screen_pos = real_pos - camera.pos

    def toData(self):
        return [self.screen_pos.x, self.screen_pos.y, self.light_radius, self.light_strength, *self.color, 0]

