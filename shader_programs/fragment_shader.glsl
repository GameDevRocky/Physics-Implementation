#version 330 core


#define MAX_LIGHTSOURCES 100
#define MAX_BRIGHTNESS 1.0

uniform sampler2D UI_tex;
uniform sampler2D Game_tex[7]; 
uniform sampler2DArray liquid_textures;
uniform sampler2DArray background_textures;

uniform vec2 resolution;

uniform vec3 transition_color;
uniform float ui_transition_weight = 0;
uniform float game_transition_weight = 0;

uniform float screen_brightness = 0;
uniform int active_layers; 
uniform float world_brightness;

uniform int background_index;

uniform mat2x4 liquid_data[10]; 

uniform int ld_length;
uniform vec4 liquid_color;

uniform int tile_size;
uniform vec2 camera_pos;

uniform int ls_length;
uniform mat2x4 lightsource_data[MAX_LIGHTSOURCES];

uniform float zoom;

uniform float time = 0;
out vec4 color; 
in vec2 uvs; 

vec4 apply_background(vec2 uvs) {
    float aspect_ratio = resolution.x / resolution.y;
    vec2 aspect_corrected_uvs = vec2(uvs.x, uvs.y / aspect_ratio);

    vec2 new_uvs = aspect_corrected_uvs + camera_pos / resolution * 0.25;

    float repeatY = 1.0; 
    float yRepeat = floor(new_uvs.y * repeatY);
    bool isOdd = mod(yRepeat, 2.0) > 0.0;       
    new_uvs.y = isOdd ? (1.0 - fract(new_uvs.y * repeatY)) / repeatY : fract(new_uvs.y * repeatY) / repeatY;
    vec4 texColor = texture(background_textures, vec3(new_uvs * 5, background_index));
    return texColor;
}

vec4 apply_light(vec4 texColor, vec2 uvs) {
    vec3 accumulated_light = vec3(0.0); // To accumulate light effects
    // Calculate aspect ratio correction
    float aspect_ratio = resolution.x / resolution.y;
    vec2 aspect_corrected_uvs = vec2(uvs.x, uvs.y / aspect_ratio);

    for (int i = 0; i < min(ls_length, MAX_LIGHTSOURCES); i++) {
        vec2 light_position = lightsource_data[i][0].xy / resolution;
        vec2 aspect_corrected_light_position = vec2(light_position.x, light_position.y / aspect_ratio);

        float light_strength = lightsource_data[i][0].w;
        float light_radius = lightsource_data[i][0].z;
        vec3 light_tint = lightsource_data[i][1].rgb;
        
        float distance_to_light = distance(aspect_corrected_uvs, aspect_corrected_light_position);
        float light_intensity = 1.0 - smoothstep(0.0, light_radius / 100, distance_to_light);
        accumulated_light += light_intensity * light_strength * mix(vec3(1.0), light_tint, light_intensity);   
    }

    texColor.rgb *= clamp(world_brightness + accumulated_light, 0.0, MAX_BRIGHTNESS);
    return texColor;
}
vec2 warp_liquid_uvs(vec2 uvs){
    float wave_amplitude = 0.01;  // Controls how much the UVs are distorted
    float wave_frequency = 20.0; // Controls the frequency of the waves
    float wave_speed = 0.02;      // Controls the speed of wave motion
    uvs.x += wave_amplitude * sin(uvs.y * wave_frequency + time * wave_speed);
    uvs.y += wave_amplitude * cos(uvs.x * wave_frequency + time * wave_speed);
    uvs.x -= time * 0.0025;
    return uvs;
}


vec4 warp_liquid_shader(vec4 texColor, vec2 uvs) {
    float wave_speed = 1;      // Speed of wave motion
    for (int i = 0; i < ld_length; i++) {
        float x = liquid_data[i][0][0]/resolution.x; 
        float y = liquid_data[i][0][1]/resolution.y; 
        float w = liquid_data[i][0][2]/resolution.x; 
        float h = liquid_data[i][0][3]/resolution.y; 
        float tex_index = liquid_data[i][1][0];
        if (uvs.x > x && uvs.x < x + w &&
        uvs.y > y && uvs.y < y + h){
            if (texColor.rgb == vec3(0, 1, 0)){
            return texColor;
            }
            if (texColor.rgb == vec3(1, 0, 0)){
                vec2 local_uvs = (uvs - vec2(x, y)) / vec2(0.3, 0.3);
                texColor = texture(liquid_textures, vec3(warp_liquid_uvs(local_uvs), tex_index));
                texColor.rgb *= 0.5;
                texColor.a = 1;
                return texColor;
            }
            if (texColor == liquid_color){
            vec2 local_uvs = (uvs - vec2(x, y)) * vec2(6, 6);
            texColor = texture(liquid_textures, vec3(warp_liquid_uvs(local_uvs), tex_index));
            texColor.a = 1.0;
            return texColor;
            }
        }
    }
    return texColor;
}



vec4 joinGameTextures(vec4 layers[5], int active_layers, vec4 background_color) {
    vec4 merged_layers = background_color;
    for (int i = 0; i < active_layers; i++) {
        merged_layers = mix(merged_layers, layers[i], layers[i].a);
    }
    return merged_layers;
}

vec4 limit_zoom_view(vec4 texColor, vec2 uvs){
    if (uvs.x > 0 && uvs.x < 1 && uvs.y > 0 && uvs.y < 1){
        return texColor;
    }
    return vec4(0);
}

void main() {

    vec2 scaled_uvs = uvs;
    scaled_uvs -= 0.5;
    scaled_uvs /= zoom;
    scaled_uvs += 0.5;

    vec4 UI_Color = texture(UI_tex, uvs); 
    UI_Color.rgb = mix(UI_Color.rgb, transition_color, ui_transition_weight);
    vec4 game_layers[5];

    for (int i = 0; i < active_layers; i++) {
        game_layers[i] =  texture(Game_tex[i], scaled_uvs);
        float blend_factor = 1.0 - float(active_layers - 1 - i) / float(active_layers); 
        game_layers[i] = warp_liquid_shader(game_layers[i], scaled_uvs);
        game_layers[i].rgb *= blend_factor;

    }
    vec4 bg_color = apply_background(scaled_uvs);
    vec4 Game_Color = joinGameTextures(game_layers, active_layers, bg_color);
    Game_Color = limit_zoom_view(Game_Color, scaled_uvs);
    Game_Color = apply_light(Game_Color, scaled_uvs);
    Game_Color.rgb = mix(Game_Color.rgb, transition_color, game_transition_weight);
    vec4 texColor = mix(Game_Color, UI_Color, UI_Color.a);
    texColor.rgb *= screen_brightness;
    color = texColor;
}
