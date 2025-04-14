import pygame
import pygame.freetype
import pygame_gui
from pygame_gui.core.interfaces import IContainerLikeInterface
import pygame_gui.core.ui_font_dictionary
import pygame_gui.ui_manager
from pygame_gui.core import ObjectID, UIElement
from pygame_gui.elements import*
import asyncio
import json
import os
from managers import EditorManager
from pygame.mixer import*
from functools import partial
from objects import*
from Input import InputHandler
import pygame.freetype
from collections.abc import Iterable
import pygame_gui.windows.ui_colour_picker_dialog


class MenuManager:
    def __init__(self, app) -> None:
        from managers import EditorManager, AssetsManager
        from App import Application
        
        self.app : Application = app
        self.editor_manager : EditorManager = self.app.editor_manager
        self.assets : AssetsManager = self.app.assets_manager
        self.input : InputHandler = app.input
        self.screen = pygame.Surface((app.SCREEN_WIDTH, app.SCREEN_HEIGHT)).convert_alpha()
        self.screen.set_colorkey((0, 0, 0))
        self.settings = self.loadSettings('data/Menu_Settings/settings.json')
        self.startMenu = StartMenu(app, self)
        self.settingsMenu = SettingsMenu(app, self)
        self.gamePlayMenu = GamePlayMenu(app, self)
        self.loadingMenu = LoadingMenu(app, self)
        self.pauseMenu = PauseMenu(app, self)
        self.levelSelectionMenu = LevelSelectionMenu(app, self)
        self.editorMenu = EditorMenu(app, self)
        self.current_menu = self.startMenu
        self.menus = [self.startMenu, self.settingsMenu]
        self.brightness = 1
        self.generatorTasks = {'fade_out' : self.fade_out()}
        self.transitioning = True
        self.transition_task = None
        self.fade_steps = 30
        self.transition_task = self.fade_out()
        self.settingsMenu.updateSettings()


    def update(self, deltaTime):
        self.screen.fill((0,0,0,0))
        font = pygame.freetype.Font(None, 16)
        font.render_to(self.screen, (self.app.SCREEN_WIDTH - 50, 20), str(int(self.app.clock.get_fps())), fgcolor= (255,255,255))
        self.current_menu.update(deltaTime)
        self.GeneratorTasks()
        for menu in self.menus:
            menu.alwaysUpdate()

    def loadSettings(self, filePath):
            with open(filePath, 'r') as file:
                return json.load(file)
    
    def process_events(self, event):
        self.current_menu.process_events(event)

    def loadMenu(self, menu, startevent = None, middle_event = None, end_event = None):
        self.generatorTasks['loadMenu'] = self.fade_out_and_in(menu, startevent, middle_event, end_event)

    def GeneratorTasks(self):
        for key, task in self.generatorTasks.items():
            try:    
                next(task)
            except StopIteration:
                task = None

    def fade_out_and_in(self, new_menu, start_event = None, middle_event = None, end_event = None):
        if callable(start_event):
            start_event()
        if isinstance(start_event, Iterable):
            for _ in start_event:
                try:
                    next(start_event)
                except:
                    break
                yield
        self.current_menu.close()

        for i in range(self.fade_steps):
            self.brightness += 1 / self.fade_steps
            self.brightness = max(0, self.brightness)
            yield  

        self.current_menu = new_menu
        if callable(middle_event):
            middle_event()
        if isinstance(middle_event, Iterable):
            for _ in middle_event:
                next(middle_event)
            yield

        self.current_menu.open()

        for i in range(self.fade_steps):
            self.brightness -= 1 / self.fade_steps
            self.brightness = min(1, self.brightness)
            yield 

        if callable(end_event):
            end_event()
        if isinstance(end_event, Iterable):
            for _ in end_event:
                next(end_event)
            yield

        yield

    def fade_in(self):
        self.brightness = 0
        for i in range(self.fade_steps):
            self.brightness += 1 / self.fade_steps
            self.brightness = max(0, self.brightness)
            yield

    def fade_out(self):
        self.brightness = 1
        for i in range(self.fade_steps):
            self.brightness -= 1 / self.fade_steps
            self.brightness = min(1, self.brightness)
            yield

    def InitializeGame(self):
        return
        self.loadMenu(self.loadingMenu)
        self.editor_manager.Initialize()
        self.loadingMenu.setView(self.editor_manager.getProgress)
        self.loadingMenu.event = self.LoadGame


    def InitializeEditor(self, levelpath):
        self.loadMenu(self.loadingMenu)
        self.editor_manager.load_level(levelpath)
        self.loadingMenu.setView(self.editor_manager.get_level_loaded_percentage)
        self.loadingMenu.event = self.LoadGame


    def LoadGame(self):
        self.transitioning = True
        self.transition_task = self.fade_out_and_in(self.editorMenu)
        self.loadMenu(self.editorMenu)
        self.editor_manager.active = True
        self.app.EditorLoop()


    
class Menu:
    def __init__(self, app, menu_manager: MenuManager) -> None:
        from App import Application
        self.app : Application = app 
        self.menu_manager = menu_manager
        self.editor_manager= self.app.editor_manager
        self.ui_manager = pygame_gui.UIManager((app.SCREEN_WIDTH, app.SCREEN_HEIGHT))
        self.ui_manager.get_theme().load_theme('data/UIThemes/Default.json')

    def update(self, deltaTime):
        self.ui_manager.update(deltaTime)
        self.ui_manager.draw_ui(self.menu_manager.screen)

    def process_events(self, event):
        self.ui_manager.process_events(event)

    def close(self):
        for sprite in self.ui_manager.ui_group.sprites():
            if type(sprite) is pygame_gui.elements.UIButton:
                sprite.disable()
        pass

    def open(self):
        for sprite in self.ui_manager.ui_group.sprites():
            if type(sprite) is pygame_gui.elements.UIButton:
                sprite.enable()
        pass
    
    def alwaysUpdate(self):
        pass

    

class StartMenu(Menu):
    def __init__(self, app, menuManager: MenuManager ) -> None:
        super().__init__(app,menuManager)
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0,0,app.SCREEN_WIDTH, app.SCREEN_HEIGHT),
            manager= self.ui_manager
        )
        self.start_button = pygame_gui.elements.UIButton(
            relative_rect= pygame.Rect(0, -100, 200, 100),
            text= 'Start',
            manager= self.ui_manager,
            anchors= {'center' : 'center'},
            container= self.panel
        )
        self.settings_button = pygame_gui.elements.UIButton(
            relative_rect= pygame.Rect(0, 0, 200, 100),
            text= 'Settings',
            manager= self.ui_manager,
            command= lambda: self.menu_manager.loadMenu(self.menu_manager.settingsMenu),
            anchors= {'center' : 'center'},
            container= self.panel
        )
        self.editor_button = pygame_gui.elements.UIButton(
            relative_rect= pygame.Rect(0, 100, 200, 100),
            text= 'Editor',
            manager= self.ui_manager,
            command= lambda: self.menu_manager.loadMenu(self.menu_manager.levelSelectionMenu),
            anchors= {'center' : 'center'},
            container= self.panel
        )

class SettingsMenu(Menu):
    def __init__(self, app, menuManager: MenuManager) -> None:
        super().__init__(app, menuManager)
        
        
        self.settings : dict = menuManager.settings
    

        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0,0,app.SCREEN_WIDTH, app.SCREEN_HEIGHT),
            manager= self.ui_manager
        )

        self.title = UILabel(relative_rect= pygame.Rect(0,0,200,100),
                             text= "SETTINGS",
                             container= self.panel,
                             anchors= {'top' : 'top', 'centerx' : 'centerx'},
                             manager= self.ui_manager,
                             object_id = ObjectID(object_id= '@Title'))


        self.scrollingContainer = UIScrollingContainer( 
            relative_rect = pygame.Rect(0,100,500, 300),
            manager= self.ui_manager,
            container= self.panel,
            allow_scroll_x= False,
            allow_scroll_y= True,
            anchors= {'centerx': 'centerx'}
            )
        self.scrollingContainer.set_scrollable_area_dimensions((0,2000))
    

        self.back_button = pygame_gui.elements.UIButton(
            relative_rect= pygame.Rect(10, 10, 100, 50),
            text= 'BACK',
            manager= self.ui_manager,
            command= lambda: self.menu_manager.loadMenu(self.menu_manager.startMenu),
            
            container= self.panel
        )
        
        self.brightness_scroll = SettingSlider(
            relative_rect= pygame.Rect(0, 0, 400, 50),
            manager= self.ui_manager,
            container= self.scrollingContainer,
            anchors= {'centerx': 'centerx', 'top' : 'top'},
            object_id= ObjectID(object_id='@SettingSlider'),
            text= 'Brightness'
            
        )
        self.volume_slider = SettingSlider(
            relative_rect= pygame.Rect(0, 50, 400, 50),
            manager= self.ui_manager,
            container= self.scrollingContainer,
            anchors= {'centerx': 'centerx', 'top' : 'top'},
            object_id= ObjectID(object_id='@SettingSlider'),
            text= 'Volume'
            
        )

        
        self.title.set_active_effect(pygame_gui.TEXT_EFFECT_TYPING_APPEAR)

    def update(self,deltaTime):
        super().update(deltaTime)
    
    def alwaysUpdate(self):
        self.updateSettings()
        super().alwaysUpdate()

    def updateSettings(self):    
        self.settings['screen_brightness'] = self.brightness_scroll.slider.get_current_value()/100
        self.settings['ui_transition_weight'] = self.menu_manager.brightness
        self.settings['volume'] = self.volume_slider.slider.get_current_value()/100
    
    def open(self):
        self.title.set_active_effect(pygame_gui.TEXT_EFFECT_TYPING_APPEAR, {'time_per_letter' : 0.15})
        self.brightness_scroll.label.set_active_effect(pygame_gui.TEXT_EFFECT_TYPING_APPEAR, {'time_per_letter' : 0.15})
        self.volume_slider.label.set_active_effect(pygame_gui.TEXT_EFFECT_TYPING_APPEAR, {'time_per_letter' : 0.15})
        super().open()

class LevelSelectionMenu(Menu):
    def __init__(self, app, menuManager: MenuManager) -> None:
        super().__init__(app, menuManager)
        files_and_dirs = os.listdir('data\Levels')
        files = [f for f in files_and_dirs if os.path.isdir(os.path.join('data\Levels', f))]
        self.buttons = []

        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0,0,app.SCREEN_WIDTH, app.SCREEN_HEIGHT),
            manager= self.ui_manager
        )
        self.levelsContainer = ScrollableContainer(
            relative_rect= pygame.Rect(app.SCREEN_WIDTH/2 + 20 ,20, app.SCREEN_WIDTH/2 - 40, app.SCREEN_HEIGHT - 40),
            manager = self.ui_manager,
            container = self.panel,
            allow_scroll_x= False,
            allow_scroll_y= True,
            scroll_dimension= (0, 1000),
            text= 'Levels'
        )
        
        for index, name in enumerate(files):
            button = UIButton(
                relative_rect= pygame.Rect(0, index * 50, app.SCREEN_WIDTH/2 - 100, 50),
                manager= self.ui_manager, container= self.levelsContainer.scrollableContainer,
                text= name.replace('.json', ''),
                command= self.create_level_command(name), 
                anchors= {'top' : 'top', 'centerx' : 'centerx'}
                )
            
            self.buttons.append(button)
        
        self.createSettingsContainer()

    def update(self, deltatime):
        
        super().update(deltatime)
    
    def createSettingsContainer(self):
        self.level_data = {}
        self.settingsContainer = UITabContainer(
            relative_rect= pygame.Rect(20,20,self.app.SCREEN_WIDTH/2 - 40, self.app.SCREEN_HEIGHT - 40),
            anchors = {'left' : 'left'},
            manager = self.ui_manager,
            container = self.panel,
        )
        
        tab_1 = self.settingsContainer.add_tab('test','num')
        self.width_entry = UITextEntryLine(
            relative_rect= pygame.Rect(20, 20, 60, 50),
            manager= self.ui_manager,
            container= self.settingsContainer.get_tab(tab_1)['container'],
            placeholder_text= "Width"
        )
        self.width_entry.set_allowed_characters('numbers')
        self.width_entry.set_text_length_limit(3)

        self.height_entry = UITextEntryLine(
            relative_rect= pygame.Rect(20, 70, 60, 50),
            manager= self.ui_manager,
            container= self.settingsContainer.get_tab(tab_1)['container'],
            placeholder_text= "Height"
        )
        self.height_entry.set_allowed_characters('numbers')
        self.height_entry.set_text_length_limit(3)

        self.layers_entry = UITextEntryLine(
            relative_rect= pygame.Rect(20, 120, 60, 50),
            manager= self.ui_manager,
            container= self.settingsContainer.get_tab(tab_1)['container'],
            placeholder_text= "Layers"
        )
        self.layers_entry.set_allowed_characters('numbers')
        self.layers_entry.set_text_length_limit(3)

        self.tileSize_entry = UITextEntryLine(
            relative_rect= pygame.Rect(20, 170, 60, 50),
            manager= self.ui_manager,
            container= self.settingsContainer.get_tab(tab_1)['container'],
            placeholder_text= "Tile Size"
        )
        self.layers_entry.set_allowed_characters('numbers')
        self.layers_entry.set_text_length_limit(3)

        self.name_entry = UITextEntryLine(
            relative_rect= pygame.Rect(20, 220, 60, 50),
            manager= self.ui_manager,
            container= self.settingsContainer.get_tab(tab_1)['container'],
            placeholder_text= "Name"
        )

        self.create_level_button = UIButton(
            relative_rect= pygame.Rect(20, 270, 60, 50),
            text= 'Create',
            manager= self.ui_manager,
            container= self.settingsContainer.get_tab(tab_1)['container'],
            command= self.addLevel
        )
    
    def create_level_command(self, name):
            return lambda: self.menu_manager.InitializeEditor(name)

    def addLevel(self):
        name = self.level_data['name']
        if name == "":
            name = f'Level{len(os.listdir("data/Levels")) + 1}'
        button = UIButton(
                relative_rect= pygame.Rect(0, len(self.buttons) * 50, 100, 50),
                manager= self.ui_manager, container= self.levelsContainer.scrollableContainer,
                text= name,
                command= self.create_level_command(name), 
                anchors= {'top' : 'top', 'centerx' : 'centerx'}
                )
        self.buttons.append(button)
        self.editor_manager.create_new_level(self.level_data)
        self.width_entry.text = ''
        self.height_entry.text = ''
        self.layers_entry.text = ''
        self.tileSize_entry.text = ''
        print(self.level_data)

    def update(self, deltatime):
        self.level_data = {
            'name' : self.name_entry.text,
            'width' : self.width_entry.text,
            'height' : self.height_entry.text,
            'layers' : self.layers_entry.text,
            'tileSize': self.tileSize_entry.text
        }
        super().update(deltatime)

class SettingSlider(UIPanel):
    def __init__(self, relative_rect, text = '', **kwargs):
        super().__init__(relative_rect, **kwargs)
        self.label = UILabel(pygame.Rect(0,0,100, 50), text= text, 
                            manager= self.ui_manager, container= self,
                            anchors= {'centery' : 'centery'}, 
                            object_id= ObjectID(object_id='@SettingSlider')
                            )
        self.label.set_active_effect(pygame_gui.TEXT_EFFECT_TYPING_APPEAR, {'time_per_letter' : 0.15})
        slider_rect = pygame.Rect(-100, 10, 100, 30)
        self.slider = pygame_gui.elements.UIHorizontalSlider(relative_rect=slider_rect, 
                                        manager= self.ui_manager, container= self, 
                                        value_range= (50, 100),
                                        start_value= 100, anchors= {'right' : 'right'},
                                        object_id= ObjectID(object_id='@SettingSlider'))

        
class ScrollableContainer(UIPanel):
    def __init__(self, relative_rect, text = '', scroll_dimension = (0, 0),
                 allow_scroll_x = True, allow_scroll_y = True, **kwargs):
        super().__init__(relative_rect, **kwargs)
        self.scrollableContainer = UIScrollingContainer(
            relative_rect= pygame.Rect(10,30, self.relative_rect.w - 10, self.relative_rect.h - 30),
            manager= self.ui_manager,
            container= self,
            allow_scroll_x= allow_scroll_x,
            allow_scroll_y= allow_scroll_y,
            anchors= {'top' : 'top', 
                      'left' : 'left',
                      'right' : 'right', 'bottom' : 'bottom'}
        )
        self.scrollableContainer.set_scrollable_area_dimensions(scroll_dimension)
        if allow_scroll_x:
            self.scrollableContainer.horiz_scroll_bar.left_button.hide()
            self.scrollableContainer.horiz_scroll_bar.right_button.hide()
        if allow_scroll_y:
            self.scrollableContainer.vert_scroll_bar.top_button.hide()
            self.scrollableContainer.vert_scroll_bar.bottom_button.hide()
        self.scrollableContainer.rebuild()

        self.label = UILabel(
            relative_rect= pygame.Rect(0,0,self.relative_rect.w, 30),
            text= text, manager= self.ui_manager,
            container= self,
            anchors= {'centerx' : 'centerx' , 'top' : 'top'}
        )



class EditorMenu(Menu):
    def __init__(self, app, menuManager: MenuManager) -> None:
        super().__init__(app, menuManager)
        self.level = None
        self.window = UIWindow(rect= pygame.Rect(15,15,250, self.app.SCREEN_HEIGHT), 
                             manager= self.ui_manager, resizable= True)
        self.container = ScrollableContainer(
            relative_rect= pygame.Rect(0,0,250, self.app.SCREEN_HEIGHT),
            manager= self.ui_manager,
            scroll_dimension= (1000, 500),
            container= self.window,
            anchors= {'top' : 'top', 
                      'left' : 'left',
                      'right' : 'right', 'bottom' : 'bottom'},
            text= 'EDITOR'
            )
        
        self.CreateTerrainContainer()
        self.CreateFruitContainer()
        self.CreateTrapsContainer()
        self.CreatePathFollowerContainer()
        self.CreateLiquidsContainer()
        self.CreateGrassContainer()
        
        self.backButton = UIButton(
            relative_rect= pygame.Rect(15,0,50,50),
            manager= self.ui_manager,
            text= 'Back', container= self.container.scrollableContainer, 
            anchors= {'top' : 'top', 'left' : 'left'},
            command= self.ReturnHome)

        self.saveButton = UIButton(
            relative_rect= pygame.Rect(65,0,50,50),
            manager= self.ui_manager,
            text= 'Save', container= self.container.scrollableContainer, 
            anchors= {'top' : 'top', 'left' : 'left'},
            command= self.editor_manager.save_current_level)

        self.del_objects_button = UIButton(
            relative_rect= pygame.Rect(115,0,100,50),
            manager= self.ui_manager,
            text= 'del objs', container= self.container.scrollableContainer, 
            anchors= {'top' : 'top', 'left' : 'left'},
            command= lambda : self.level.init_remove_all_objects())
        
        self.del_tiles_button = UIButton(
            relative_rect= pygame.Rect(215,0,100,50),
            manager= self.ui_manager,
            text= 'del tiles', container= self.container.scrollableContainer, 
            anchors= {'top' : 'top', 'left' : 'left'},
            command= lambda : self.level.init_remove_all_tiles())


        self.layerSelection = UIDropDownMenu(
            relative_rect= pygame.Rect(15,300,100,50),
            starting_option= '1',
            manager= self.ui_manager,
            container= self.container.scrollableContainer, 
            options_list= ['1'],
            anchors= {'top' : 'top', 'left' : 'left'}) 
        
        self.backgroundSelection = UIDropDownMenu(
            relative_rect= pygame.Rect(115,300,100,50),
            starting_option= '1',
            manager= self.ui_manager,
            container= self.container.scrollableContainer, 
            options_list= ['1'],
            anchors= {'top' : 'top', 'left' : 'left'}) 
        
        self.brightness_slider = SettingSlider(
            relative_rect= pygame.Rect(15,350,300,50),
            manager= self.ui_manager,
            container= self.container.scrollableContainer,
            object_id= ObjectID(object_id='@SettingSlider'),
            text= 'Brightness'
            
        )
        self.brightness_slider.slider.value_range = (0, 100)

        self.zoom_slider = SettingSlider(
            relative_rect= pygame.Rect(315,350,300,50),
            manager= self.ui_manager,
            container= self.container.scrollableContainer,
            object_id= ObjectID(object_id='@SettingSlider'),
            text= 'Zoom'
            
        )
        self.zoom_slider.slider.value_range = (-100, 100)
        
        self.savingProgressBar = UIProgressBar(
            relative_rect= pygame.Rect(-100, -30, 100, 30),
            anchors= {'right' : 'right', 'bottom' : 'bottom'},
            manager= self.ui_manager
        )

        self.savingProgressBar.percent_method = self.editor_manager.get_level_saved_percentage

    def CreateTerrainContainer(self):
        rounded_square = pygame.image.load('data\Assets\Terrain\Rounded Square.png').convert_alpha()
        self.tilesScrollingContainer = ScrollableContainer(
            pygame.Rect(15,100,100, 200),
            manager= self.ui_manager,
            container= self.container.scrollableContainer,
            text= 'TILES',
            scroll_dimension= (0, 500), allow_scroll_x=False
        )
        index = 0
        for tile_type, values in self.menu_manager.assets.tile_assets.items():
            img : pygame.Surface
            img = values.get('full')
            if img:
                button = UIButton(
                relative_rect= pygame.Rect(0,index * 50, 32,32),
                manager= self.ui_manager,
                text= '', container= self.tilesScrollingContainer.scrollableContainer, 
                anchors= {'centerx' : 'centerx', 'top' : 'top'},
                command= self.create_object_command('tile', tile_type, None, None),            
                )
                base_img = pygame.transform.smoothscale(rounded_square,img.get_size())
                darkened_shade = pygame.transform.solid_overlay(base_img, (0,0,0,100))
                lightened_shade = pygame.transform.solid_overlay(base_img, (255,255,255,100))
                base_img.blit(img, (0,0), special_flags= pygame.BLEND_RGBA_ADD)
                button.selected_image = base_img.copy()
                button.normal_image = base_img.copy()
                button.hovered_image = base_img.copy()
                button.selected_image.blit(darkened_shade, (0,0), special_flags= pygame.BLEND_RGBA_MULT)
                button.hovered_image.blit(lightened_shade, (0,0),  special_flags= pygame.BLEND_RGBA_MULT)
                button.rebuild()
                index += 1

    def CreateFruitContainer(self):
        self.fruitScrollingContainer = ScrollableContainer(
            pygame.Rect(115,100,100, 200),
            manager= self.ui_manager,
            container= self.container.scrollableContainer,
            text= 'FRUIT',
            scroll_dimension= (0, 500), allow_scroll_x=False
        )
    
        index = 0
        for object_type, object in self.menu_manager.assets.object_assets.items():
            if object['class'] is Fruit:
                if object_type == 'Collected':
                    continue

                img = object['standstill']
                img : pygame.Surface
                button = UIButton(
                relative_rect= pygame.Rect(0,index * 50, 50,50),
                manager= self.ui_manager,
                text= '', container= self.fruitScrollingContainer.scrollableContainer, 
                anchors= {'centerx' : 'centerx', 'top' : 'top'},
                command= self.create_object_command('object', object_type, Fruit, {'fruit_type' : object_type }),            
                )
                button.set_tooltip(text= object_type, delay= 0.5)
                img = pygame.transform.smoothscale_by(img, 1.5)
                darkened_shade = pygame.transform.solid_overlay(img, (0,0,0,100))
                lightened_shade = pygame.transform.solid_overlay(img, (255,255,255,100))
                button.selected_image = img.copy()
                button.normal_image = img.copy()
                button.hovered_image = img.copy()
                button.selected_image.blit(darkened_shade, (0,0), special_flags= pygame.BLEND_RGBA_MULT)
                button.hovered_image.blit(lightened_shade, (0,0),  special_flags= pygame.BLEND_RGBA_MULT)
                button.rebuild()
                index += 1

    def CreateTrapsContainer(self):
        self.trapsScrollingContainer = ScrollableContainer(
            pygame.Rect(215,100,100, 200),
            manager= self.ui_manager,
            container= self.container.scrollableContainer,
            text= 'TRAPS',
            scroll_dimension= (0, 500), allow_scroll_x=False
        )
        index = 0
        for object_type, object in self.menu_manager.assets.object_assets.items():
            if issubclass(object['class'], Trap):
                img = object['standstill']
                img : pygame.Surface
                button = UIButton(
                relative_rect= pygame.Rect(0,index * 50, 50,50),
                manager= self.ui_manager,
                text= '', container= self.trapsScrollingContainer.scrollableContainer, 
                anchors= {'centerx' : 'centerx', 'top' : 'top'},
                command= self.create_object_command('object', object_type, object['class'], {}),            
                )
                button.set_tooltip(text= object_type, delay= 0.5)
                bounding_rect = img.get_bounding_rect(min_alpha= 255)
                img = pygame.Surface.subsurface(img, bounding_rect)
                img = pygame.transform.smoothscale_by(img, 1.5)
                darkened_shade = pygame.transform.solid_overlay(img, (0,0,0,100))
                lightened_shade = pygame.transform.solid_overlay(img, (255,255,255,100))
                button.selected_image = img.copy()
                button.normal_image = img.copy()
                button.hovered_image = img.copy()
                button.selected_image.blit(darkened_shade, (0,0), special_flags= pygame.BLEND_RGBA_MULT)
                button.hovered_image.blit(lightened_shade, (0,0),  special_flags= pygame.BLEND_RGBA_MULT)
                button.rebuild()
                index += 1

    def CreatePathFollowerContainer(self):
        self.pathFollowerScrollingContainer = ScrollableContainer(
            pygame.Rect(315,100,100, 200),
            manager= self.ui_manager,
            container= self.container.scrollableContainer,
            text= 'MOVERS',
            scroll_dimension= (0, 500), allow_scroll_x=False
        )
        index = 0
        for object_type, object in self.menu_manager.assets.object_assets.items():
            if issubclass(object['class'], PathFollower):
                img = object['standstill']
                img : pygame.Surface
                button = UIButton(
                relative_rect= pygame.Rect(0,index * 50, 50,50),
                manager= self.ui_manager,
                text= '', container= self.pathFollowerScrollingContainer.scrollableContainer, 
                anchors= {'centerx' : 'centerx', 'top' : 'top'},
                command= self.create_object_command('path', object_type, object['class'], {'pathRect' : lambda: self.editor_manager.editor.selector_rect}),            
                )
                button.set_tooltip(text= object_type, delay= 0.5)
                bounding_rect = img.get_bounding_rect(min_alpha= 255)
                img = pygame.Surface.subsurface(img, bounding_rect)
                img = pygame.transform.smoothscale_by(img, 1.5)
                darkened_shade = pygame.transform.solid_overlay(img, (0,0,0,100))
                lightened_shade = pygame.transform.solid_overlay(img, (255,255,255,100))
                button.selected_image = img.copy()
                button.normal_image = img.copy()
                button.hovered_image = img.copy()
                button.selected_image.blit(darkened_shade, (0,0), special_flags= pygame.BLEND_RGBA_MULT)
                button.hovered_image.blit(lightened_shade, (0,0),  special_flags= pygame.BLEND_RGBA_MULT)
                button.rebuild()
                index += 1
    
    def CreateLiquidsContainer(self):
        self.liquidsScrollingContainer = ScrollableContainer(
            pygame.Rect(415,100,100, 200),
            manager= self.ui_manager,
            container= self.container.scrollableContainer,
            text= 'LIQUIDS',
            scroll_dimension= (0, 500), allow_scroll_x=False
        )
        index = 0
        for object_type, object in self.menu_manager.assets.object_assets.items():
            if issubclass(object['class'], Liquid) or object['class'] is Liquid:
                img = object['standstill']
                img : pygame.Surface
                button = UIButton(
                relative_rect= pygame.Rect(0,index * 50, 50,50),
                manager= self.ui_manager,
                text= '', container= self.liquidsScrollingContainer.scrollableContainer, 
                anchors= {'centerx' : 'centerx', 'top' : 'top'},
                command= self.create_object_command('liquid', object_type, object['class'], {'body_rect' : lambda: self.editor_manager.editor.selector_rect}),            
                )
                button.set_tooltip(text= object_type, delay= 0.5)
                bounding_rect = img.get_bounding_rect(min_alpha= 255)
                img = pygame.Surface.subsurface(img, bounding_rect)
                img = pygame.transform.smoothscale_by(img, 1.5)
                darkened_shade = pygame.transform.solid_overlay(img, (0,0,0,100))
                lightened_shade = pygame.transform.solid_overlay(img, (255,255,255,100))
                button.selected_image = img.copy()
                button.normal_image = img.copy()
                button.hovered_image = img.copy()
                button.selected_image.blit(darkened_shade, (0,0), special_flags= pygame.BLEND_RGBA_MULT)
                button.hovered_image.blit(lightened_shade, (0,0),  special_flags= pygame.BLEND_RGBA_MULT)
                button.rebuild()
                index += 1
    
    def CreateGrassContainer(self):
        self.grassScrollingContainer = ScrollableContainer(
            pygame.Rect(515,100,100, 200),
            manager= self.ui_manager,
            container= self.container.scrollableContainer,
            text= 'GRASS',
            scroll_dimension= (0, 500), allow_scroll_x=False
        )
        index = 0
        for object_type, object in self.menu_manager.assets.object_assets.items():
            if issubclass(object['class'], Grass_Generator) or object['class'] is Grass_Generator:
                img = object['standstill']
                img : pygame.Surface
                button = UIButton(
                relative_rect= pygame.Rect(0,index * 50, 50,50),
                manager= self.ui_manager,
                text= '', container= self.grassScrollingContainer.scrollableContainer, 
                anchors= {'centerx' : 'centerx', 'top' : 'top'},
                command= self.create_object_command('object', object_type, object['class'], {}),            
                )
                button.set_tooltip(text= object_type, delay= 0.5)
                bounding_rect = img.get_bounding_rect(min_alpha= 255)
                img = pygame.Surface.subsurface(img, bounding_rect)
                img = pygame.transform.smoothscale_by(img, 1.5)
                darkened_shade = pygame.transform.solid_overlay(img, (0,0,0,100))
                lightened_shade = pygame.transform.solid_overlay(img, (255,255,255,100))
                button.selected_image = img.copy()
                button.normal_image = img.copy()
                button.hovered_image = img.copy()
                button.selected_image.blit(darkened_shade, (0,0), special_flags= pygame.BLEND_RGBA_MULT)
                button.hovered_image.blit(lightened_shade, (0,0),  special_flags= pygame.BLEND_RGBA_MULT)
                button.rebuild()
                index += 1

    def create_object_command(self, editor_type, type, obj_class, object_args ):
            return lambda: self.SetEditorType(editor_type, type, obj_class, object_args)

    def SetEditorType(self, edit_type, type, object_class, object_args):
        self.editor_manager.refactor_editor(edit_type, type, object_class, object_args)

    def ReturnHome(self):
        self.menu_manager.loadMenu(self.menu_manager.levelSelectionMenu, startevent= self.editor_manager.close)
        
        
    def open(self):
        self.level = self.editor_manager.current_level
        self.layerSelection.remove_options(self.layerSelection.options_list)
        self.backgroundSelection.remove_options(self.backgroundSelection.options_list)
        self.layerSelection.add_options([str(layer + 1) for layer in range(self.level.layers)])
        self.backgroundSelection.add_options([str(bg + 1) for bg in range(self.app.assets_manager.background_assets['num_textures'])])
        self.layerSelection.rebuild()
        if self.level:

            self.brightness_slider.slider.set_current_value(self.level.settings['saved_settings']['world_brightness'] * 100)
            self.zoom_slider.slider.set_current_value(0)
        self.brightness_slider.rebuild()
        self.zoom_slider.rebuild()
        self.backgroundSelection.rebuild()
        return super().open()

    def update(self, deltatime):
        if self.window.hover_point(*pygame.mouse.get_pos()):
            self.editor_manager.editor.active = False
        else:
            self.editor_manager.editor.active = True
        self.level.current_layer = int(self.layerSelection.selected_option[0]) - 1
        self.level.current_background = int(self.backgroundSelection.selected_option[0]) - 1
        self.level.settings['saved_settings']['world_brightness'] = self.brightness_slider.slider.get_current_value()/100
        self.level.settings['saved_settings']['background'] = self.level.current_background
        self.level.camera.zoom = 1 + self.zoom_slider.slider.current_value/100
        self.savingProgressBar.current_progress = self.editor_manager.get_level_saved_percentage()

        super().update(deltatime)
        pass

        
class GamePlayMenu(Menu):
    def __init__(self, app, menuManager: MenuManager) -> None:
        super().__init__(app, menuManager)
        self.pauseButton =pygame_gui.elements.UIButton(
            relative_rect= pygame.Rect(10, 10, 100, 50),
            text= '||',
            manager= self.ui_manager,
            command= lambda: self.pause(),
        )
    def pause(self):
        self.menu_manager.loadMenu(self.menu_manager.pauseMenu)

class LoadingMenu(Menu):
    def __init__(self, app, menuManager: MenuManager) -> None:
        super().__init__(app, menuManager)
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0,0,app.SCREEN_WIDTH, app.SCREEN_HEIGHT),
            manager= self.ui_manager
        )
        self.progressBar = UIProgressBar(
            relative_rect=  pygame.Rect(0,0,200,50),
            container= self.panel,
            manager= self.ui_manager,
            anchors= {'center' : 'center'})
        self.event = None
        

    def update(self, deltaTime):
        self.progressBar.current_progress = self.editor_manager.get_level_loaded_percentage()
        if self.progressBar.current_progress >= 100:
                self.load()
        super().update(deltaTime)

    def load(self):
        if callable(self.event):
                event = self.event
                self.event = None
                event()

    def setView(self, method):
        self.progressBar.percent_method = method

class PauseMenu(Menu):
    def __init__(self, app, menuManager: MenuManager) -> None:
        super().__init__(app, menuManager)
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(0,0,200, 200),
            manager= self.ui_manager,
            anchors= {'center' : 'center'}
        )
        self.continueButton = UIButton(
            relative_rect= pygame.Rect(0,-50,100, 50),
            text= 'CONTINUE',
            manager= self.ui_manager,
            anchors= {'center' : 'center'},
            command= lambda: self.menu_manager.loadMenu(self.menu_manager.gamePlayMenu),
            container= self.panel
        )
        self.homeButton = UIButton(
            relative_rect= pygame.Rect(0,50,100, 50),
            text= 'HOME',
            manager= self.ui_manager,
            anchors= {'center' : 'center'},
            command= self.ReturnStartScreen,
            container= self.panel
        )
    def ReturnStartScreen(self):
        self.menu_manager.loadMenu(self.menu_manager.startMenu)
        self.app.MainMenuLoop()
