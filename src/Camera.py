import pygame
from Input import InputHandler
class Camera:
    def __init__(self, level, input : InputHandler) -> None:
        from levels import Level
        self.level : Level = level
        self.pos = pygame.Vector2(0,0)
        self.velocity = pygame.Vector2(0,0)
        self.input = input
        self.speed = 1
        self.friction = 0.9
        self.focus = None
        self.rect = pygame.Rect(0, 0, self.level.manager.app.SCREEN_WIDTH,self.level.manager.app.SCREEN_HEIGHT)
        self.clamp = False
        self.zoom = 1

    def update(self, deltatime):
        if self.focus:
            pass
        else:
            self.unBound(deltatime)  
            self.update_rect()

    def update_rect(self):
        self.rect.topleft = self.pos          

    def unBound(self, deltatime):
        self.velocity.x += (self.input.EditorAction.right - self.input.EditorAction.left) * self.speed
        self.velocity.y += (self.input.EditorAction.down - self.input.EditorAction.up) * self.speed
        self.pos += self.velocity
        self.velocity *= self.friction
        if self.clamp:
            self.pos.x = pygame.math.clamp(self.pos.x, self.level.bounding_rect.left, self.level.bounding_rect.right - self.level.manager.app.SCREEN_WIDTH)
            self.pos.y = pygame.math.clamp(self.pos.y, self.level.bounding_rect.top, self.level.bounding_rect.bottom - self.level.manager.app.SCREEN_HEIGHT)
        


        
