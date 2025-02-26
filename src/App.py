import pygame
import sys
import moderngl
from pygame.color import Color
from Shader import Shader
from UI_Manager import MenuManager
from managers import *
from Input import InputHandler

class Application:
    
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 400
    FPS = 60

    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init()
        self.window = pygame.Window(title='Game',size= (self.SCREEN_WIDTH, self.SCREEN_HEIGHT),
                                     position= pygame.WINDOWPOS_CENTERED,
                                     opengl = True, always_on_top = True)
        self.ctx = moderngl.create_context()
        self.screen = self.window.get_surface()
        self.clock = pygame.time.Clock()
        self.input = InputHandler()
        self.assets_manager = AssetsManager(self)
        self.editor_manager = EditorManager(self)
        self.menu_manager = MenuManager(self)
        self.shader = Shader(self, self.ctx, 'shader_programs/vertex_shader.glsl','shader_programs/fragment_shader.glsl', data= None)
        self.deltaTime = 0
        self.running = True 

    def EditorLoop(self):
        while self.editor_manager.active:
            self.deltaTime = self.clock.tick(self.FPS)/1000
            self.update()
            self.menu_manager.update(self.deltaTime)
            self.editor_manager.update(self.deltaTime)
            self.render()
            self.input.keyboard.clear()
            self.window.flip()

    def MainMenuLoop(self):
        while self.running:
            self.deltaTime = self.clock.tick(self.FPS)/1000.0
            self.update()
            self.menu_manager.update(self.deltaTime)
            self.render()
            self.input.keyboard.clear()
            self.window.flip()
            
    def update(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            self.menu_manager.process_events(event)
            self.input.update(event)

    def render(self):
        if self.editor_manager.current_level:
            game_screens = self.editor_manager.current_level.screens
            if len(game_screens) > 1:
                screen = game_screens.pop(self.editor_manager.current_level.current_layer)
                game_screens.insert(0, screen)
        else:
            game_screens = []
        self.shader.apply(self.menu_manager.screen, game_screens)


if __name__ == '__main__': 
    app = Application()
    app.MainMenuLoop()