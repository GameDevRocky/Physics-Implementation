import random
import pygame
from pygame.math import Vector2
from lightsource import LightSource
from random import randint
from typing import Callable, Union
from collision_categories import CTYPES
from types import GeneratorType
import math
import pygame.gfxdraw
import pymunk
from levels import Level

class GameObject():

    def __init__(self, pos : Vector2 = Vector2(0,0), orientation : Vector2 = Vector2(0,1), 
                 type : str = '', layer : int = 0, level = None) -> None:
                
        self.level : Level = level
        self.initialized_pos = Vector2(pos)
        self.pos = Vector2(pos)
        self.orientation = Vector2(orientation)
        self.type = type
        self.layer = layer
        self.rect = None
        self.img = None
        self.state = None
        object_cache = self.level.manager.assets.object_assets.get(self.type)
        self.img = object_cache['standstill']
        self.scale = object_cache['scale']
        self.size = Vector2(object_cache['size'](self.level)) * self.scale
        self.img = pygame.transform.smoothscale(self.img, self.size)
        self.rect = self.img.get_rect()
        self.animation_generator = None
        self.generator_tasks = {}
        self.active = True
        self.canCover = False
        self.frame_rate = 3
        self.tick = 0

        self.createPhysicsBody()
    
    def update(self, deltatime):
        self.tick += 1
        self.pos = Vector2(self.body.position.x, self.body.position.y) + self.offset
        self.rect.center = self.pos
        pass

    def createPhysicsBody(self):
        cache = self.level.manager.assets.object_assets[self.type]    
        shape_type = cache['shape_type']
        self.mass = cache['mass']
        self.friction = cache['friction']
        self.elasticity = cache['elasticity']
        self.body_type = cache['body_type']
        self.offset = cache['offset'](self.level) if callable(cache['offset']) else cache['offset']
        self.body : pymunk.Body = None
        self.shape : pymunk.Shape = None
        if shape_type == 'circle':
            self.radius = self.img.get_bounding_rect(253).width
            self.moment = cache['moment'](self.mass, self.radius)
            self.body = pymunk.Body(self.mass, self.moment, self.body_type)
            self.shape = cache['shape'](self.body, self.radius)
        elif shape_type == 'poly':
            self.radius = cache['radius']
            self.moment = cache['moment'](self.mass, self.size)
            self.body = pymunk.Body(self.mass, self.moment, self.body_type)
            self.shape = cache['shape'](self.body, self.size, self.radius)
        
        self.body.position = tuple(self.pos)
        self.shape.elasticity = self.elasticity
        self.shape.friction = self.friction
        self.shape.filter = pymunk.ShapeFilter(
            categories= cache['categories'],
            mask= cache['mask']
        )
        self.shape.collision_type = cache['categories']
        
    def remove(self):
        return None

    def Animate(self, frames, loop= False, next_animation = None):
        for frame in frames:
            img = pygame.transform.smoothscale(frame, self.size)            
            self.img = img
            for i in range(self.frame_rate):
                yield
            yield
        if loop:
            yield GameObject.Animate(self, frames, loop= True)

        elif next_animation:
            yield next_animation
        else:
            yield

    def getRotated_img(self, img, rect):
        angle = self.body.angular_velocity
        new_img = pygame.transform.rotate(img, angle)
        new_rect = new_img.get_rect(center = rect.center)
        return new_img, new_rect

    def run_tasks(self):
        for key, task in self.generator_tasks.items():
            try:    
                returned_task = next(task)
                if returned_task:
                    self.generator_tasks[key] = returned_task
            except StopIteration:
                task = None

    def initialize(self):
        return None
        self.pos = Vector2(self.initialized_pos)
        self.rect.center = self.pos
        self.body.position = tuple(self.pos)
        self.body.velocity = (0,0)
        

    def idle(self, deltatime):
            
            pass
    
    def ToDict(self):
        data = {
            'pos' : tuple(self.initialized_pos),
            'orientation' : tuple(self.orientation),
            'type' : self.type,
            'layer' : self.layer
        }
        return data

    

class Fruit(GameObject):
    
    def __init__(self, pos: Vector2 = Vector2(0, 0), orientation: Vector2 = Vector2(0, 1), 
                 type: str = '', layer: int = 0, level= None, fruit_type = None) -> None:
        super().__init__(pos, orientation, type, layer, level)
        
        self.state = 'idle'
        self.fruit_type = fruit_type
        self.idle_frames = self.level.manager.assets.object_assets[self.fruit_type]['default_frames']
        self.collected_frames = self.level.manager.assets.object_assets[self.fruit_type]['collected_frames']
        self.animation_generator = super().Animate(self.idle_frames, loop= True)
        self.canCover = False     

    def idle(self, deltatime):
        self.Animate()
        super().update(deltatime)

    def update(self, deltatime):
        self.Animate()
        super().update(deltatime)

    def Animate(self):
        try:
            returned_task = next(self.animation_generator)
            if isinstance(returned_task, GeneratorType):
                self.animation_generator = returned_task
        except:
            match self.state:
                case 'idle':
                    self.animation_generator = super().Animate(self.idle_frames)
                case 'collected':
                    self.set_active(False)    
                
    def remove(self):
        super().remove()
        self.animation_generator = super().Animate(self.collected_frames, next_animation= self.set_state('collected'))

        return -1
    def set_active(self, active):
        self.active = active
        print(self.active)
        
    def set_state(self, state):
        self.state = state
        print(self.state)
        yield

    def ToDict(self):
        data = {**super().ToDict(), **{'fruit_type' : self.fruit_type}}
        return data

class Trap(GameObject):
    
    def __init__(self, pos: Vector2 = Vector2(0, 0), orientation: Vector2 = Vector2(0, 0), 
                 type: str = '', layer: int = 0, level= None) -> None:
        super().__init__(pos, orientation, type, layer, level)

    def remove(self):
        return None

class Fire(Trap, LightSource):
    
    def __init__(self, pos: Vector2 = Vector2(0, 0), orientation: 
                 Vector2 = Vector2(0, 0), type: str = '', layer: int = 0, level= None) -> None:
        
        super().__init__(pos, orientation, type, layer, level)
        LightSource.__init__(self, self.pos - self.level.camera.pos) 
        self.on_frames = self.level.manager.assets.object_assets.get(self.type)['on_frames']
        self.hit_frames = self.level.manager.assets.object_assets.get(self.type)['activate_frames']
        self.off_frames = self.level.manager.assets.object_assets.get(self.type)['off_frames']
        self.frame_rate = 2
        self.state = 'activate'
        self.animation_generator = super().Animate(self.hit_frames)   
        self.light_radius = self.level.tile_size/3

        self.light_strength = 2    
        self.generator_tasks = {'createSparks' : self.generateSparks(), 'flick' : self.flicker()}
        self.size.y *= 2
        self.rect.size = self.size
        

    def idle(self, deltatime):
        self.Animate()
        self.updatePos(self.pos, self.level.camera)
        self.run_tasks()
        super().update(deltatime)   

    def Animate(self):
        try:
            next(self.animation_generator)
        except:
            match self.state:
                case 'on':
                    self.animation_generator = super().Animate(self.on_frames)
                case 'activate':
                    self.state = 'on'
    def flicker(self):


        self.light_strength = randint(100, 200)/100
        for _ in range(self.frame_rate):
            yield
        yield self.flicker()

    def generateSparks(self):
        from particles import Spark
        iterations = randint(20, 120)
        for _ in range(iterations):
            yield
        spark = Spark(pos= self.pos, orientation= Vector2(0,1), type = 'Particle',
                                                layer= self.layer, level= self.level, velocity= Vector2(randint(-50, 50),-50) )
        self.level.add_object_to_queue(spark)
        yield self.generateSparks()   

    def run_tasks(self):
        if self.state == 'on':
            super().run_tasks()


    def update(self, deltatime):
        super().update(deltatime) 

class Spike(Trap):
    
    def __init__(self, pos = Vector2(0, 0), orientation = Vector2(0, 0), type = '', layer = 0, level= None):
        super().__init__(pos, orientation, type, layer, level)
        
        self.idle_frames = self.level.manager.assets.object_assets.get(self.type)['idle_frames']

    def idle(self, deltatime):
        super().update(deltatime)

    def update(self, deltatime):
        super().update(deltatime)

class PathFollower(GameObject):
        
    class Node:
        def __init__(self, pos):
            self.pos = pos  # Current position (Vector2)
            self.velocity = pygame.Vector2(0, 0)  # Velocity
            self.acceleration = pygame.Vector2(0, 0)  # Acceleration
            self.previous = None  # Reference to previous node
            self.next = None  # Reference to next node

        def apply_force(self, force):
            self.acceleration += force

        def update(self, deltatime):
            # Update velocity and position
            self.velocity += self.acceleration * deltatime
            self.pos += self.velocity * deltatime
            self.acceleration = pygame.Vector2(0, 0)  # Reset acceleration


    def __init__(self, pos=pygame.Vector2(0, 0), orientation=pygame.Vector2(0, 0),
                 type='', layer=0, level= None,
                 pathRect: Union[Callable[[], tuple[int, int, int, int]], pygame.Rect] = pygame.Rect(0, 0, 0, 0)):
        super().__init__(pos, orientation, type, layer, level)
        if callable(pathRect):
            self.pathRect = pygame.Rect(*pathRect())
        else:
            self.pathRect = pygame.Rect(*pathRect)
        
        self.nodes = self.CreateNodes()
        min_distance = 20
        self.target_node = self.bottomright
        for node in self.nodes:
            if distance := (self.pos - node.pos).length() < min_distance:
                min_distance = distance
                self.target_node = node

        self.pos = pygame.Vector2(self.target_node.pos)
        self.velocity = pygame.Vector2(0, 0) 
        self.speed = 100
        self.max_speed = 200

    def idle(self, deltatime):
        
        self.followPath(deltatime)
        super().update(deltatime)

    def followPath(self, deltatime):
        if self.move_towards_node(self.target_node, deltatime):
            self.target_node = self.target_node.next

    def move_towards_node(self, target_node: 'PathFollower.Node', deltatime):
        target_node_pos = pymunk.Vec2d(target_node.pos[0],target_node.pos[1])
        direction = target_node_pos - self.body.position

        if direction.length < 3: 
            self.reachedNode() 
            self.body.velocity = pymunk.Vec2d(0,0)  
            self.body.position = pymunk.Vec2d(target_node.pos[0],target_node.pos[1])   
            return True 
        
        direction = direction.normalized()
        acceleration = direction * self.speed  
        self.body.velocity += acceleration * deltatime
        if self.body.velocity.length > self.max_speed:
            self.body.velocity.scale_to_length(self.max_speed)

        self.body.position += self.body.velocity * deltatime
        return False  

    def CreateNodes(self):
        self.pathRect.normalize()
        self.bottomright = PathFollower.Node(self.pathRect.bottomright)
        self.bottomleft = PathFollower.Node(self.pathRect.bottomleft)
        self.topleft = PathFollower.Node(self.pathRect.topleft)
        self.topright = PathFollower.Node(self.pathRect.topright)
        
        self.topleft.next = self.topright
        self.topright.next = self.bottomright
        self.bottomright.next = self.bottomleft
        self.bottomleft.next = self.topleft

        return [self.topleft, self.topright, self.bottomleft, self.bottomright]  
    
    def reachedNode(self):
        pass

    def ToDict(self):
        """Serialize the state into a dictionary."""
        data = {**super().ToDict(), **{'pathRect': [self.pathRect.topleft, self.pathRect.size]}}
        return data

class RockHead(PathFollower):
    
    def __init__(self, pos=Vector2(0, 0), orientation=Vector2(0, 0), type='', 
                 layer=0, level= None, pathRect= pygame.Rect(0, 0, 0, 0)):
        super().__init__(pos, orientation, type, layer, level, pathRect)
        
        self.idle_frames = self.level.manager.assets.object_assets[self.type]['idle_frames']
        self.bottom_hit_frames = self.level.manager.assets.object_assets[self.type]['bottom_hit_frames']
        self.top_hit_frames = self.level.manager.assets.object_assets[self.type]['top_hit_frames']
        self.right_hit_frames = self.level.manager.assets.object_assets[self.type]['right_hit_frames']
        self.left_hit_frames = self.level.manager.assets.object_assets[self.type]['left_hit_frames']
        self.blink_frames = self.level.manager.assets.object_assets[self.type]['blink_frames']
        self.frame_rate = 1
        self.state = 'idle'
        self.animation_generator = super().Animate(self.idle_frames, loop= True)
        

    def idle(self, deltatime):
        self.Animate()
        super().idle(deltatime)

    def reachedNode(self):
        direction = self.CalculateVelocityDirection()
        match direction:
            case 'right': 
                self.animation_generator = super().Animate(self.right_hit_frames)
            case 'left': 
                self.animation_generator = super().Animate(self.left_hit_frames)
            case 'bottom': 
                self.animation_generator = super().Animate(self.bottom_hit_frames)
            case 'top': 
                self.animation_generator = super().Animate(self.top_hit_frames)
            case _: 
                self.animation_generator = super().Animate(self.idle_frames)
        
    
    def Animate(self):
        try:
            returned_task = next(self.animation_generator)
            if returned_task:
                self.animation_generator = returned_task
        except:
            self.animation_generator = super().Animate(self.idle_frames)


    def CalculateVelocityDirection(self):
        if abs(self.body.velocity.x) > abs(self.body.velocity.y):
            return 'right' if self.body.velocity.x > 0 else 'right'
        elif abs(self.body.velocity.y) > abs(self.body.velocity.x):
            return 'bottom' if self.body.velocity.y > 0 else 'top'

class Saw(PathFollower):
    
    def __init__(self, pos=pygame.Vector2(0, 0), orientation=pygame.Vector2(0, 0), type='', layer=0, level= None, pathRect = pygame.Rect(0, 0, 0, 0)):
        super().__init__(pos, orientation, type, layer, level, pathRect)
        
        self.on_frames = self.level.manager.assets.object_assets[self.type]['on_frames']
        self.off_frames = self.level.manager.assets.object_assets[self.type]['off_frames']
        self.state = 'on'
        self.animation_generator = super().Animate(self.on_frames, True)
        self.frame_rate = 2

    def idle(self, deltatime):
        self.Animate()
        super().idle(deltatime)
    

    def Animate(self):
        try:
            returned_task = next(self.animation_generator)
            if returned_task:
                self.animation_generator = returned_task
        except:
            print('couldnt loop')
            self.animation_generator = super().Animate(self.on_frames, True)

class PlatForm(PathFollower):
    def __init__(self, pos=pygame.Vector2(0, 0), orientation=pygame.Vector2(0, 0), type='', layer=0, level= None, pathRect = pygame.Rect(0, 0, 0, 0)):
        super().__init__(pos, orientation, type, layer, level, pathRect)
        self.speed = 250
        self.wait_period = 60

    def idle(self, deltatime):
        return super().idle(deltatime)
    
    def move_towards_node(self, target_node: 'PathFollower.Node', deltatime):
        target_node_pos = pymunk.Vec2d(target_node.pos[0],target_node.pos[1])
        direction = target_node_pos - self.body.position

        if direction.length < 3: 
            self.reachedNode() 
            self.body.velocity = pymunk.Vec2d(0,0)  
            self.body.position = pymunk.Vec2d(target_node.pos[0],target_node.pos[1])   
            return True 
        
        direction = direction.normalized()
        acceleration = direction * self.speed * 10
        self.body.velocity = acceleration * deltatime
        if self.body.velocity.length > self.max_speed:
            self.body.velocity.scale_to_length(self.max_speed)

        self.body.position += self.body.velocity * deltatime
        return False  

    def add_movement(arbiter, space : pymunk.Space, data):
        # Get the platform and object bodies
        platform_body = arbiter.shapes[0].body  # Assuming shape[0] is the platform
        object_body = arbiter.shapes[1].body   # Assuming shape[1] is the colliding object
        object_body.friction = 1.0
        # Set the object's velocity to match the platform's velocity
        object_body.velocity = platform_body.velocity * 2
        # Adjust the object's position relative to the platform
        relative_position = object_body.position - platform_body.position
        object_body.position = platform_body.position + relative_position

        return False




class Liquid(GameObject):
    SPRING_CONSTANT = 0.02
    DIRECTION_CONTANT = 0.001
    DAMPING = 0.98
    MAX_VELOCITY = 15

    class Node(GameObject):
        def __init__(self, pos = Vector2(0, 0), orientation = Vector2(0, 1), type = '', layer = 0,  level=None, render_pos = Vector2(0,0)):
            super().__init__(pos, orientation, type, layer, level)
            self.render_pos = render_pos
            self.starting_pos = Vector2(pos)
            self.body.velocity = (0,0)
            self.shape.sensor = True
            self.img.set_alpha(0)
            
        def remove(self):
            return -1
        
        def ToDict(self):
            return None

        def idle(self, deltatime):
            
            direction = Vector2(self.starting_pos - self.body.position)
            self.body.velocity += tuple(direction * Liquid.DIRECTION_CONTANT)
            self.body.position += self.body.velocity
            self.render_pos += self.body.velocity
            super().update(deltatime)

    
    def __init__(self, pos = Vector2(0, 0), orientation = Vector2(0, 1), 
                 type = '', layer = 0, level= None, body_rect = pygame.Rect(0,0,0,0)):
        super().__init__(pos, orientation, type, layer, level)
        if callable(body_rect):
            self.body_rect = pygame.Rect(*body_rect())
        else:
            self.body_rect = pygame.Rect(*body_rect)        
        self.body_rect.normalize()
        self.size = self.body_rect.size
        self.rect = self.body_rect.copy()
        self.pos = Vector2(self.body_rect.center)
        self.body.position = tuple(self.pos)
        self.color = (255,255,255)
        self.img.set_colorkey((0,0,0))
        self.nodes = []
        self.shape.sensor = True
        self.render_img = None
        self.img.fill((0,0,0))
        self.texture_index = self.level.manager.assets.object_assets[self.type]['texture_index']
        self.surrounding_terrain = []
        if not self.body_rect == pygame.Rect(0,0,0,0):
            self.img = pygame.Surface(self.rect.size).convert_alpha()
            self.render_img = self.img.copy()
            self.color = self.level.manager.assets.object_assets[self.type]['color']
            self.rect = self.img.get_rect(center= self.body.position)
            self.rect.normalize()
        else:
            self.active = False
        if self.active:
            self.create_nodes()
            self.get_surrounding_terrain()
            #self.nodes[int(len(self.nodes) / 2)].body.velocity = (0, -5)
    
    def create_nodes(self):
        for x in range(0, int(math.floor(self.rect.size[0])), int(math.floor(self.level.tile_size)/2)):
            pos = Vector2(int(math.floor(self.rect.left)) + x, self.rect.top + self.level.tile_size)
            render_pos = Vector2(x, self.level.tile_size)
            node = Liquid.Node(pos= pos, orientation= Vector2(0,1), type= 'Liquid_Node', layer= self.layer, level= self.level, render_pos= render_pos)
            self.nodes.append(node)
            self.level.add_object_to_queue(node)

    def get_surrounding_terrain(self):
        for x in range(int(self.body_rect.left), int(self.body_rect.right + self.level.tile_size), int(self.level.tile_size)):
            for y in range(int(self.body_rect.top), int(self.body_rect.bottom + self.level.tile_size), int(self.level.tile_size)):
                row = self.level.terrain.get((math.floor(x/self.level.tile_size),math.floor(y/self.level.tile_size)))
                if row:
                    tile = row.get(self.layer)
                    self.surrounding_terrain.append(tile)

    def render_polygon(self):
        rect = self.img.get_rect()
        points = [
            rect.bottomleft,      
            rect.topleft + Vector2(0, self.level.tile_size)
        ]
        
        for node in self.nodes:
            points.append(node.render_pos)  
        
        points.extend([
            rect.topright + Vector2(0, self.level.tile_size),       
            rect.bottomright 
        ])        
        
        if len(points) > 2:
            pygame.gfxdraw.filled_polygon(self.img, points, self.color)
            points = points[1:]
            points = points[:-1]
            pygame.draw.lines(self.img, (255,255,250), False, points, 1)


    def idle(self, deltatime):
        if self.active:
            self.img.fill((0, 0, 0, 0))
        
            self.update_nodes(deltatime)
            self.render_polygon()
            self.body.velocity = (0,0)
            super().update(deltatime)
            self.body_rect.center = self.rect.center

    def update_nodes(self, deltatime):
       
        for i in range(len(self.nodes)):
            node = self.nodes[i]

            # Validate node position and velocity
            if math.isnan(node.body.position.y) or math.isnan(node.body.velocity.y):
                node.body.position.y = 0
                node.body.velocity.y = 0

            if i > 0:  # Left neighbor
                left_node = self.nodes[i - 1]
                left_diff = node.body.position.y - left_node.body.position.y
                if not math.isnan(left_diff):  # Ensure the difference is valid
                    left_force = -self.SPRING_CONSTANT * left_diff
                    node.body.velocity = (node.body.velocity.x, node.body.velocity.y + left_force)
                    left_node.body.velocity = (left_node.body.velocity.x, left_node.body.velocity.y - left_force)
            
            if i < len(self.nodes) - 1:  # Right neighbor
                right_node = self.nodes[i + 1]
                right_diff = node.body.position.y - right_node.body.position.y
                if not math.isnan(right_diff):  # Ensure the difference is valid
                    right_force = -self.SPRING_CONSTANT * right_diff
                    node.body.velocity = (node.body.velocity.x, node.body.velocity.y + right_force)
                    right_node.body.velocity = (right_node.body.velocity.x, right_node.body.velocity.y - right_force)

            # Apply damping to reduce excessive velocity over time
            node.body.velocity = pymunk.Vec2d(
                max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, node.body.velocity.x)),
                max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, node.body.velocity.y))
            ) * self.DAMPING
            
            
            node.idle(deltatime)

    def splash(arbiter : pymunk.Arbiter, space, data):
        arbiter.shapes[0].body.velocity = (0, arbiter.shapes[1].body.velocity.y/200)
        return True

    def slow_down(arbiter : pymunk.Arbiter, space, data):
        liquid_shape, other_shape = arbiter.shapes

        other_shape.body.velocity -= (0,1)
        print("slowing down")
        return False

    def ToDict(self):
        """Serialize the state into a dictionary."""
        data = {**super().ToDict(), **{'body_rect': [self.body_rect.topleft, self.body_rect.size]}}
        return data
    
    def remove(self):
        self.active = False
        for node in self.nodes:
            node.active = False
        return None

class Spring(Trap):
    
    def __init__(self, pos = Vector2(0, 0), orientation = Vector2(0, 1), type = '', layer = 0, level= None):
        super().__init__(pos, orientation, type, layer, level)
        self.idle_frames = self.level.manager.assets.object_assets[self.type]['idle_frames']
        self.activate_frames = self.level.manager.assets.object_assets[self.type]['activate_frames']
        self.deactivate_frames = self.level.manager.assets.object_assets[self.type]['deactivate_frames']
        self.on_frames = self.level.manager.assets.object_assets[self.type]['on_frames']
        self.animation_generator = super().Animate(self.idle_frames, loop= True)   

        self.state = 'idle'       
        self.wait_period = 60

    def Initialize(self):
        self.collision_handlers += self.level.create_collision_handlers(self.id, Fire, CTYPES.SPRING, CTYPES.FIRE)
        for handler in self.collision_handlers:
            handler.begin = self.InitiateCollision
            handler.pre_solve = self.activate
            handler.seperate = self.deactivate
            #handler.seperate = 
        return super().Initialize()

    def idle(self, deltatime):
        self.run_tasks()
        self.updateHandlers()
        self.Animate()
        super().update(deltatime)

    def Animate(self):
        try:
            task = next(self.animation_generator)
            if task:
                self.animation_generator = task
        except:
            self.animation_generator = super().Animate(self.idle_frames)
        

    def updateHandlers(self):
        for obj in Spring.QUEUE:
            if isinstance(obj, Fire):
                handler = self.level.space.add_collision_handler(CTYPES.SPRING | self.id, CTYPES.FIRE | Fire.ID)
                handler.begin = self.InitiateCollision
                handler.pre_solve = self.activate
                handler.seperate = self.deactivate

    def activate(self, arbiter, space, data):
        if self.state == 'activate':
            arbiter.shapes[1].body.apply_impulse_at_world_point((0,-2000), arbiter.shapes[1].body.position)
       
        return False

    def deactivate(self, arbiter, space, data):
        self.state = 'deactivate'
        self.animation_generator =  super().Animate(self.deactivate_frames, next_animation=super().Animate(self.idle_frames, loop= True))
    
    def InitiateCollision(self, arbiter, space, data):
        self.state = 'waiting'
        print('begin')
        self.generator_tasks['wait'] = self.wait()
        return True

    def wait(self):
        for i in range(self.wait_period):
            yield
        self.state = 'activate'
        self.animation_generator = super().Animate(self.activate_frames, next_animation=super().Animate(self.on_frames, loop= True))


class Pendulum(PathFollower):
    def __init__(self, pos=pygame.Vector2(0, 0), orientation=pygame.Vector2(0, 0), type='', layer=0, level=None, pathRect = pygame.Rect(0, 0, 0, 0)):
        super().__init__(pos, orientation, type, layer, level, pathRect)
        if callable(pathRect):
            self.pathRect = pygame.Rect(*pathRect())
        else:
            self.pathRect = pygame.Rect(*pathRect)

        body = pymunk.Body(100, pymunk.moment_for_circle(100, 0, 5), pymunk.Body.STATIC)
        self.anchor = pymunk.Circle(body, 5)
        self.anchor.body.position = tuple(self.pathRect.topleft)
        self.constraint = pymunk.PinJoint(self.anchor.body, self.body, (0,0), (0,0))


    def idle(self, deltatime):
        super().update(deltatime)


class Grass_Generator(GameObject):
    def __init__(self, pos = Vector2(0, 0), orientation = Vector2(0, 1), type = '', layer = 0, level=None):
        super().__init__(pos, orientation, type, layer, level)
        self.color = self.level.manager.assets.object_assets[self.type]['color']
        self.shape.sensor = True
        self.increment = self.level.tile_size/4
        self.create_grass()
        self.img.set_alpha(0)

    def create_grass(self):
        for x in range(0, self.rect.width, int(self.increment)):
            grass = Grass(Vector2(self.pos + self.rect.midleft + Vector2(x - self.rect.w/2, 0)), Vector2(0,1), 'Grass', self.layer, self.level, randint(0, 4))
            color = pygame.Vector3(self.color)
            color *= randint(50, 100)/100
            grass.img = pygame.transform.solid_overlay(grass.img, color)
            grass.orig_img = grass.img.copy()
            self.level.add_object_to_queue(grass)
        
    def idle(self, deltatime):
        super().update(deltatime)

class Grass(GameObject):
    def __init__(self, pos = Vector2(0, 0), orientation = Vector2(0, 1), type = '', layer = 0, level=None, variation = 0):
        super().__init__(pos, orientation, type, layer, level)
        self.shape.sensor = True
        self.variation = variation
        self.img = self.level.manager.assets.object_assets[self.type]['img_variations'][self.variation].copy()
        self.img = pygame.transform.scale(self.img, Vector2(self.size) * self.scale)
        self.canCover = True
        self.offset_rotation = random.uniform(-5, 5)
        self.speed = random.randint(2, 10)
        self.sway = random.randint(10, 30)
        self.windSway = random.randint(1, 3) * pygame.math.clamp(random.random(), 0.1, 1.0)
        self.orig_img = self.img.copy()

    def idle(self, deltatime):
        super().update(deltatime)
        self.angle = math.sin(self.tick / self.sway) * self.speed + self.offset_rotation
        self.offset_rotation += (0 - self.offset_rotation) / self.sway
        self.img = pygame.transform.rotate(self.orig_img, self.angle)
    
    def ToDict(self):
        return None

class Fan(Trap):
    def __init__(self, pos = Vector2(0, 0), orientation = Vector2(0, 1), type = '', layer = 0, level=None):
        super().__init__(pos, orientation, type, layer, level)
        self.detection_rect = self.rect.copy()
        self.detection_rect.inflate(0, 200)
        self.on_frames = self.level.manager.app.assets_manager.object_assets[self.type]['on_frames']
        self.off_frames = self.level.manager.app.assets_manager.object_assets[self.type]['off_frames']
        self.generator_tasks['animate'] = super().Animate(self.on_frames, True)
        self.frame_rate = 1
        

    def idle(self, deltatime):
        self.run_tasks()
        super().update(deltatime)