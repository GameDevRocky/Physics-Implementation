import pygame
import moderngl
from array import array
from collections.abc import Iterable


class Shader:
    def __init__(self, app, ctx, vert_file, frag_file, data) -> None:
        from App import Application
        self.app : Application = app
        self.ctx = ctx
        self.quad_buffer = self.ctx.buffer(data=array('f', [
            -1.0, 1.0, 0.0, 0.0,
            1.0, 1.0, 1.0, 0.0,
            -1.0, -1.0, 0.0, 1.0,
            1.0, -1.0, 1.0, 1.0,
        ]))
        with open(vert_file, 'rb') as file:
            self.vert_shader = file.read()
        with open(frag_file, 'rb') as file:
            self.frag_shader = file.read()

        self.program = self.ctx.program(vertex_shader=self.vert_shader, fragment_shader=self.frag_shader)
        self.updateSettings(self.app.menu_manager.settings)
        self.updateSettings(self.app.editor_manager.settings)
        #self.updateSettings(self.app.GameManager.settings.get('saved_settings'))


        self.time = 0
        self.render_object = self.ctx.vertex_array(self.program, [(self.quad_buffer, '2f 2f', 'vert', 'texcoord')])
        self.UI_Texture = None
        self.Game_Texture = None

    def surf_to_texture(self, surf: pygame.Surface) -> moderngl.Texture:
        surf = surf.convert_alpha()
        tex : moderngl.Texture = self.ctx.texture(surf.get_size(), 4, data=surf.get_view('1'))
        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        tex.swizzle = 'BGRA'
        return tex
    
    def surf_to_texture_class(ctx, surf):
        tex : moderngl.Texture = ctx.texture(surf.get_size(), 4, data=surf.get_view('1'))
        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        tex.swizzle = 'BGRA'
        return tex

    def surfaces_to_texture_array(ctx, surfs):
        """
        Converts a list of Pygame surfaces into a ModernGL Texture2DArray.

        Args:
            ctx: The ModernGL context.
            surfs: List of Pygame surfaces to be used as layers.

        Returns:
            A ModernGL TextureArray object.
        """
        if not surfs:
            raise ValueError("Surface list cannot be empty.")

        # Dimensions and number of layers
        width, height = surfs[0].get_size()
        layers = len(surfs)

        # Ensure all surfaces have the same size
        for surf in surfs:
            if surf.get_size() != (width, height):
                print(surf.get_size())
                raise ValueError("All surfaces must have the same dimensions.")

        # Collect and stack all surface data vertically
        data = b"".join(surf.get_view("1") for surf in surfs)

        # Create the texture array
        texture_array = ctx.texture_array(
            size=(width, height, layers),
            components=4,            # RGBA (4 channels)
            data=data,               # Pixel data stacked vertically
            alignment=1,             # Minimal padding
            dtype="f1"               # 8-bit unsigned integers
        )

        # Set filtering and swizzle
        texture_array.filter = (moderngl.NEAREST, moderngl.NEAREST)
        texture_array.swizzle = "BGRA"  # Convert BGRA -> RGBA if necessary

        return texture_array




    def apply(self, UI_Surface, Game_Surfaces):
        self.UI_Texture = self.surf_to_texture(UI_Surface)
        self.UI_Texture.use(0)

        Game_Textures = [self.surf_to_texture(surf) for surf in Game_Surfaces]
        Game_Textures.reverse()
        for index, texture in enumerate(Game_Textures):
            texture.use(location= index + 1)

        self.program['UI_tex'].value = 0
        self.program['Game_tex'].value = [1,2,3,4,5, 6,7] #tuple(range(1, len(Game_Textures) + 1))

        self.program['active_layers'].value = len(Game_Textures)
        self.program['transition_color'].write(array('f', (117/255, 200/255, 255/255)))
        self.updateSettings(self.app.menu_manager.settings)
        self.updateSettings(self.app.editor_manager.settings)
        if self.app.editor_manager.current_level:
            self.updateSettings(self.app.editor_manager.current_level.settings)
            self.updateSettings(self.app.editor_manager.current_level.shader_data)

        self.program['time'] = self.time
        self.time += 1
        self.render_object.render(mode=moderngl.TRIANGLE_STRIP)
        self.UI_Texture.release()
        for texture in Game_Textures:
            texture.release()

    def updateSettings(self, settings):
        if settings:
            for key, value in settings.items():
                if type(value) is dict:
                    try:
                        self.updateSettings(value)
                    except:
                        print('dict not working')
                        pass
                elif isinstance(value, Iterable):
                    try:
                        self.program[key].write(value)
                    except:
                        print('cant write values')
                        pass
                else:
                    try:
                        self.program[key] = value
                    except:
                        pass
        

        
