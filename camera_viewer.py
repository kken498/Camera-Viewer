import bpy
import gpu
import blf
from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent

dns = bpy.app.driver_namespace

def get_offscreen(context):
    camera_viewer = context.screen.camera_viewer
    scene = context.scene
    render = scene.render
    scale = (render.resolution_y/1080)
    width = int(render.resolution_x/scale * camera_viewer.size*camera_viewer.quality/100)
    height = int(render.resolution_y/scale * camera_viewer.size*camera_viewer.quality/100)			
    offscreen = gpu.types.GPUOffScreen(width, height, format='RGBA16F')
    return offscreen

def get_shader():
    vert_out = gpu.types.GPUStageInterfaceInfo("my_interface")
    vert_out.smooth('VEC2', "uv")

    shader_info = gpu.types.GPUShaderCreateInfo()

    shader_info.sampler(0, 'FLOAT_2D', "image")
    shader_info.vertex_in(0, 'VEC2', "pos")
    shader_info.vertex_in(1, 'VEC2', "texCoord")
    shader_info.vertex_out(vert_out)

    shader_info.push_constant('MAT4', "ModelViewProjectionMatrix")

    shader_info.fragment_out(0, 'VEC4', "fragColor")

    shader_info.vertex_source(
        "void main()"
        "{"
        "   uv = texCoord;"
        "   gl_Position = ModelViewProjectionMatrix * vec4(pos.xy, 0.0, 1.0);"
        "}"
    )

    shader_info.fragment_source(
        "void main()"
        "{"
        "  vec4 finalColor = mix(vec4(0.0), texture(image, uv), 1.0);"
        "  finalColor.rgb = pow(finalColor.rgb, vec3(2.2));"
        "  fragColor = finalColor;"
        "}"
    )

    # Create a shader from the shader info
    shader = gpu.shader.create_from_info(shader_info)
    return shader

@persistent
def check_viewer_property(self, context):
    if bpy.context.screen.camera_viewer.viewer_toggle == True:
        offscreen = get_offscreen(bpy.context)
        dns["draw_viewer_toggle"] = bpy.types.SpaceView3D.draw_handler_add(draw_viewer_toggle, (bpy.context, offscreen), 'WINDOW', 'POST_PIXEL')
        
def draw_viewport_outline():
    wdith = bpy.context.region.width-1
    height = bpy.context.region.height
    vertices = [
        (0, 0),
        (wdith, 0),
        (wdith, height),
        (0, height),
        (0, 0),
    ]
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(4)
    batch = batch_for_shader(shader, "LINE_STRIP", {"pos": vertices})
    shader.bind()

    if hasattr(bpy.context.screen, "camera_viewer"):
        pass

    if bpy.context.screen.camera_viewer.viewer_toggle == False:
        if bpy.context.screen.is_animation_playing or bpy.context.space_data.region_3d.view_perspective == 'CAMERA':

            if bpy.context.screen.is_animation_playing:
                if bpy.context.scene.sync_mode == 'FRAME_DROP':
                    shader.uniform_float("color", (1,0.85,0,1))
                elif bpy.context.scene.sync_mode == 'AUDIO_SYNC':
                    shader.uniform_float("color", (0.25,0.5,1,1))
                else:
                    shader.uniform_float("color", (1,0.35,0.35,1))
            elif bpy.context.space_data.region_3d.view_perspective == 'CAMERA':
                shader.uniform_float("color", (0.486275,1,0.67451,1))

            batch.draw(shader)

    if not (bpy.context.screen.is_animation_playing and bpy.context.screen.camera_viewer.viewer_toggle == False):
        if bpy.context.object:
            if bpy.context.scene.tool_settings.use_keyframe_insert_auto == True:
                shader.uniform_float("color", (0.5,0,0,1))
                batch.draw(shader)
            elif bpy.context.object.mode == 'POSE':
                shader.uniform_float("color", (0.6,0.6,0.6,1))

                batch.draw(shader)

        if bpy.context.space_data.shading.use_compositor == 'ALWAYS' or (bpy.context.space_data.shading.use_compositor == 'CAMERA' and bpy.context.space_data.region_3d.view_perspective == 'CAMERA'):
            shader.uniform_float("color", (0.394198,0.569371,1,1))
            batch.draw(shader)

def draw_camera_name(context, camera_viewer, camera, x, y, width, height):
    font_id = 0  # XXX, need to find out how best to get this.

    if camera:
        text = camera.name

        blf.enable(font_id, blf.SHADOW)
        if camera_viewer.lock_camera:
            color = (1,1,0,1)
        else:
            color = (1,1,1,1)
        
        blf.color(font_id, color[0], color[1], color[2], color[3])

        blf.size(font_id, 16)
        dimensions = blf.dimensions(font_id, text)

        if camera_viewer.position in {'Right-Bottom','Right-Top'}:
            blf.position(font_id, x + width - dimensions[0], y + height + 12, 0)
        else:
            blf.position(font_id, x, y + height + 12, 0)

        blf.draw(font_id, text)

        blf.disable(font_id, blf.SHADOW)

def draw_camera_statuses(context, camera_viewer, camera, x, y, width, height):
    font_id = 0  # XXX, need to find out how best to get this.

    if camera:

        blf.enable(font_id, blf.SHADOW)

        if camera_viewer.statuses == 'EDIT':
            text = f'Size - {str(round(camera_viewer.size,2))} | Quality {str(camera_viewer.quality)} %'

            if camera_viewer.quality == 50:
                blf.color(font_id, 1, 1, 0, 1)
            elif camera_viewer.size > 1.5 or camera_viewer.size < 0.5 or camera_viewer.quality > 50:
                blf.color(font_id, 1, 0, 0, 1)
            else:
                blf.color(font_id, 1, 1, 1, 1)
        elif camera_viewer.statuses == 'Navigation':
            if camera.data.type in {"PERSP",'PANO'}:
                text = f'Lens - {str(camera.data.lens)} mm'
            elif camera.data.type == 'ORTHO':
                text = f'Scale - {str(camera.data.ortho_scale)}'

            blf.color(font_id, 1, 1, 1, 1)

        blf.size(font_id, 16)
        dimensions = blf.dimensions(font_id, text)

        if camera_viewer.position in {'Right-Bottom','Right-Top'}:
            blf.position(font_id, x, y + height + 12, 0)
        else:
            blf.position(font_id, x + width - dimensions[0], y + height + 12, 0)

        blf.draw(font_id, text)

        blf.disable(font_id, blf.SHADOW)

def draw_outline(context, x, y, width, height, thickness, color):
    vertices = [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
        (x, y),
    ]

    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "LINE_STRIP", {"pos": vertices})

    shader.bind()
    if context.screen.camera_viewer.statuses == 'EDIT':
        shader.uniform_float("color", (0.394198,0.569371,1,1))
    elif context.screen.camera_viewer.statuses == 'Navigation':
        shader.uniform_float("color", (1, 0.6, 0, 1))
    elif context.screen.is_animation_playing:
        if context.scene.sync_mode == 'FRAME_DROP':
            shader.uniform_float("color", (1,0.85,0,1))
        elif context.scene.sync_mode == 'AUDIO_SYNC':
            shader.uniform_float("color", (0.25,0.5,1,1))
        else:
            shader.uniform_float("color", (1,0.35,0.35,1))
    elif bpy.context.space_data.region_3d.view_perspective == 'CAMERA':
        shader.uniform_float("color", (0.486275,1,0.67451,1))
    else:
        shader.uniform_float("color", color)

    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(thickness)
    batch.draw(shader)
    gpu.state.blend_set("NONE")

def draw_viewer_toggle(context, offscreen):
    context = bpy.context
    if context.screen.camera_viewer.viewer_toggle == True:
        camera_viewer = context.screen.camera_viewer

        if not camera_viewer.active_camera:
            if camera_viewer.lock_camera and camera_viewer.camera:
                camera = bpy.data.objects[camera_viewer.camera]
            else:
                camera = context.scene.camera
        else:
            if context.active_object.type == 'CAMERA':
                camera = context.active_object
            else:
                return
            
        if camera:

            x = camera_viewer.x
            y = camera_viewer.y
            region_width = context.region.width
            region_height = context.region.height
            for r in context.area.regions:
                if r.type == 'UI':
                    n_panel = r.width
                    break
            for r in context.area.regions:
                if r.type == 'TOOLS':
                    tool_panel = r.width
                    break

            scene = context.scene

            render = scene.render
            scale = render.resolution_y/1080
            width = int(render.resolution_x/scale * camera_viewer.size/3.5)
            height = int(render.resolution_y/scale * camera_viewer.size/3.5)

            view_matrix = camera.matrix_world.inverted()

            projection_matrix = camera.calc_matrix_camera(
                context.evaluated_depsgraph_get(), x=width, y=height)
            
            for a in bpy.data.screens[context.screen.name +' Camera Viewer'].areas:
                if a.type == 'VIEW_3D':
                    if a.spaces[0]:
                        space = a.spaces[0]
                        break

            if context.scene.render.engine == 'CYCLES' and space.shading.type in {'RENDERED'}:
                return

            offscreen.draw_view3d(
                context.scene,
                context.view_layer,
                space,
                context.region,
                view_matrix,
                projection_matrix,
                do_color_management=True)
            
            if camera_viewer.position == 'Left-Bottom':
                x = x+20
                y = y+20
            elif camera_viewer.position == 'Right-Bottom':
                x = (x+40)*-1 + region_width-width
                y = y+20
            elif camera_viewer.position == 'Left-Top':
                x = x+20 + tool_panel
                y = (y+180)*-1 + region_height-height
            elif camera_viewer.position == 'Right-Top':
                x = (x+20)*-1 + region_width-n_panel-width
                y = (y+60)*-1 + region_height-height

            shader = get_shader()

            batch = batch_for_shader(
                shader, 'TRI_FAN',
                {
                    "pos": ((x, y), (x+width,y), (x+width, y+height), (x,y+height)),
                    "texCoord": ((0,0), (1,0),(1,1),(0,1)),
                },
            )

            shader.uniform_sampler("image", offscreen.texture_color)
            batch.draw(shader)

            draw_outline(context, x, y, width, height, camera_viewer.border_thickness, camera_viewer.border_color)

            if camera_viewer.show_camera_name:

                draw_camera_name(
                                context,
                                camera_viewer,
                                camera,
                                x,
                                y,
                                width,
                                height,
                            )
                
            if camera_viewer.statuses:
                    
                draw_camera_statuses(
                                context,
                                camera_viewer,
                                camera,
                                x,
                                y,
                                width,
                                height,
                            )

class Camera_Viewer_UI_Control(bpy.types.GizmoGroup):
    bl_idname = "Camera_Viewer_UI_Control"
    bl_label = "Camera Viewer Control"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE'}

    viewer_gizmos = {}
    space = None

    def prepare_space_gizmo(self, context, space, type):
        camera_viewer = context.screen.camera_viewer
        camera_viewer_ui = context.scene.camera_viewer_ui

        gizmo = self.viewer_gizmos[type]

        if type in ('SOLID', 'MATERIAL', 'RENDERED'):
            if space.shading.type == type:
                gizmo.color = 0.0, 0.5, 1.0
                gizmo.alpha = 0.5
                gizmo.backdrop_fill_alpha = 0.7
            else:
                if context.scene.render.engine == 'CYCLES' and type == 'RENDERED':
                    gizmo.color = 1, 0, 0
                else:
                    gizmo.color = 1.0, 1.0, 1.0
                gizmo.alpha = 0.2
                gizmo.backdrop_fill_alpha = 0.1

        elif type in ('DISABLED', 'CAMERA', 'ALWAYS'):
            if space.shading.use_compositor == type:
                gizmo.color = 1.0, 0.5, 0.0
                gizmo.alpha = 0.5
                gizmo.backdrop_fill_alpha = 0.3
            else:
                gizmo.color = 1.0, 1.0, 1.0
                gizmo.alpha = 0.2
                gizmo.backdrop_fill_alpha = 0.1

        elif type == 'OVERLAY':
            if space.overlay.show_overlays:
                gizmo.color = 0.0, 0.5, 1.0
                gizmo.alpha = 0.5
                gizmo.backdrop_fill_alpha = 0.7
            else:
                gizmo.color = 1.0, 1.0, 1.0
                gizmo.alpha = 0.2
                gizmo.backdrop_fill_alpha = 0.1

        elif type == 'scene_lights':
            if space.shading.use_scene_lights:
                gizmo.color = 1.0, 0.9, 0.0
                gizmo.alpha = 0.5
                gizmo.backdrop_fill_alpha = 0.3
            else:
                gizmo.color = 1.0, 1.0, 1.0
                gizmo.alpha = 0.2
                gizmo.backdrop_fill_alpha = 0.1
        elif type == 'scene_lights_render':
            if space.shading.use_scene_lights_render:
                gizmo.color = 1.0, 0.9, 0.0
                gizmo.alpha = 0.5
                gizmo.backdrop_fill_alpha = 0.3
            else:
                gizmo.color = 1.0, 1.0, 1.0
                gizmo.alpha = 0.2
                gizmo.backdrop_fill_alpha = 0.1
        elif type == 'scene_world':
            if space.shading.use_scene_world:
                gizmo.color = 1.0, 0.9, 0.0
                gizmo.alpha = 0.5
                gizmo.backdrop_fill_alpha = 0.3
            else:
                gizmo.color = 1.0, 1.0, 1.0
                gizmo.alpha = 0.2
                gizmo.backdrop_fill_alpha = 0.1
        elif type == 'scene_world_render':   
            if space.shading.use_scene_world_render:
                gizmo.color = 1.0, 0.9, 0.0
                gizmo.alpha = 0.5
                gizmo.backdrop_fill_alpha = 0.3
            else:
                gizmo.color = 1.0, 1.0, 1.0
                gizmo.alpha = 0.2
                gizmo.backdrop_fill_alpha = 0.1
                
        gizmo.color_highlight = 1.0, 1.0, 1.0
        gizmo.alpha_highlight = 0.8
        gizmo.use_tooltip = True
        gizmo.line_width = 1
        gizmo.scale_basis = 12

        if not camera_viewer.active_camera:
            if camera_viewer.lock_camera and camera_viewer.camera:
                camera = bpy.data.objects[camera_viewer.camera]
            else:
                camera = context.scene.camera
        else:
            if context.active_object.type == 'CAMERA':
                camera = context.active_object
            else:
                camera = None

        base = not camera_viewer.viewer_toggle or bool(camera_viewer.statuses) or not camera or (context.scene.render.engine == 'CYCLES' and space.shading.type in {'RENDERED'}) or not camera_viewer_ui.use_ui

        if type in ('scene_lights', 'scene_world'):
            gizmo.hide = base or space.shading.type not in {'MATERIAL'} or not camera_viewer_ui.use_lighting
        elif type in ('scene_lights_render', 'scene_world_render'):
            gizmo.hide = base or space.shading.type not in {'RENDERED'} or not camera_viewer_ui.use_lighting
        elif type in ('DISABLED', 'CAMERA', 'ALWAYS'):
            gizmo.hide = base or space.shading.type not in {'RENDERED', 'MATERIAL'} or not camera_viewer_ui.use_compositor or not context.scene.use_nodes
        else:
            gizmo.hide = base

        return gizmo

    def draw_modify(self, context, camera_viewer, x, y, width, height, region_width, region_height, tool_panel, n_panel):
        camera_viewer_ui = context.scene.camera_viewer_ui
        space = self.space

        gizmo = self.gizmos[1]

        if camera_viewer.position == 'Left-Bottom':
            x = x+20
            y = y+20
        elif camera_viewer.position == 'Right-Bottom':
            x = (x+40)*-1 + region_width-width
            y = y+20
        elif camera_viewer.position == 'Left-Top':
            x = x+20 + tool_panel
            y = (y+180)*-1 + region_height-height
        elif camera_viewer.position == 'Right-Top':
            x = (x+20)*-1 + region_width-n_panel-width
            y = (y+60)*-1 + region_height-height

        if not camera_viewer.active_camera:
            if camera_viewer.lock_camera and camera_viewer.camera:
                camera = bpy.data.objects[camera_viewer.camera]
            else:
                camera = context.scene.camera
        else:
            if context.active_object.type == 'CAMERA':
                camera = context.active_object
            else:
                camera = None

        gizmo.hide = not camera_viewer.viewer_toggle or bool(camera_viewer.statuses) or not camera or (context.scene.render.engine == 'CYCLES' and space.shading.type in {'RENDERED'}) or not camera_viewer_ui.use_ui
        gizmo.matrix_basis[1][3] = y + height + 14 + 3
        if 'Left' in camera_viewer.position:
            gizmo.matrix_basis[0][3] = x + width - 12
        if 'Right' in camera_viewer.position:
            gizmo.matrix_basis[0][3] = x + 12

    def draw_navigation(self, context, camera_viewer, x, y, width, height, region_width, region_height, tool_panel, n_panel):
        gizmo = self.gizmos[0]
        if camera_viewer.position == 'Left-Bottom':
            x = x+20
            y = y+20
        elif camera_viewer.position == 'Right-Bottom':
            x = (x+40)*-1 + region_width-width
            y = y+20
        elif camera_viewer.position == 'Left-Top':
            x = x+20 + tool_panel
            y = (y+180)*-1 + region_height-height
        elif camera_viewer.position == 'Right-Top':
            x = (x+20)*-1 + region_width-n_panel-width
            y = (y+60)*-1 + region_height-height

        gizmo.scale_basis = 150 * camera_viewer.size
        gizmo.hide = not context.screen.camera_viewer.viewer_toggle
        gizmo.matrix_basis[0][3] = x + width/2
        gizmo.matrix_basis[1][3] = y + height/2

    def draw_space(self, context, camera_viewer, x, y, width, height, region_width, region_height, tool_panel, n_panel):
        if camera_viewer.position == 'Left-Bottom':
            x = x+20
            y = y+20
        elif camera_viewer.position == 'Right-Bottom':
            x = (x+40)*-1 + region_width-width
            y = y+20
        elif camera_viewer.position == 'Left-Top':
            x = x+20 + tool_panel
            y = (y+180)*-1 + region_height-height
        elif camera_viewer.position == 'Right-Top':
            x = (x+20)*-1 + region_width-n_panel-width
            y = (y+60)*-1 + region_height-height

        space = self.space
        scale = 14

        render_gz = self.prepare_space_gizmo(context, space, 'RENDERED')
        render_gz.matrix_basis[1][3] = y + height + scale + 3
        
        mat_gz = self.prepare_space_gizmo(context, space, 'MATERIAL')
        mat_gz.matrix_basis[1][3] = y + height + scale + 3

        sod_gz = self.prepare_space_gizmo(context, space, 'SOLID')
        sod_gz.matrix_basis[1][3] = y + height + scale + 3

        ol_gz = self.prepare_space_gizmo(context, space, 'OVERLAY')
        ol_gz.matrix_basis[1][3] = y + height + scale + 3

        dis_gz = self.prepare_space_gizmo(context, space, 'DISABLED')
        dis_gz.matrix_basis[1][3] = y + height + scale + 3

        cam_gz = self.prepare_space_gizmo(context, space, 'CAMERA')
        cam_gz.matrix_basis[1][3] = y + height + scale + 3

        al_gz = self.prepare_space_gizmo(context, space, 'ALWAYS')
        al_gz.matrix_basis[1][3] = y + height + scale + 3

        sc_li_gz = self.prepare_space_gizmo(context, space, 'scene_lights')
        sc_li_gz.matrix_basis[1][3] = y + height + scale + 3
        
        sc_wr_gz = self.prepare_space_gizmo(context, space, 'scene_world')
        sc_wr_gz.matrix_basis[1][3] = y + height + scale + 3

        rd_li_gz = self.prepare_space_gizmo(context, space, 'scene_lights_render')
        rd_li_gz.matrix_basis[1][3] = y + height + scale + 3

        rd_wr_gz = self.prepare_space_gizmo(context, space, 'scene_world_render')
        rd_wr_gz.matrix_basis[1][3] = y + height + scale + 3

        if 'Left' in camera_viewer.position:
            render_gz.matrix_basis[0][3] = x + width - scale - (scale*2)
            mat_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*2
            sod_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*3
            ol_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*4

            sc_wr_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*5
            rd_wr_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*5
            sc_li_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*6
            rd_li_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*6

            al_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*7
            cam_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*8
            dis_gz.matrix_basis[0][3] = x + width - scale - (scale*2)*9

        elif 'Right' in camera_viewer.position:
            render_gz.matrix_basis[0][3] = x + scale + (scale*2)*4
            mat_gz.matrix_basis[0][3] = x + scale + (scale*2)*3
            sod_gz.matrix_basis[0][3] = x + scale + (scale*2)*2
            ol_gz.matrix_basis[0][3] = x + scale + (scale*2)

            sc_wr_gz.matrix_basis[0][3] = x + scale + (scale*2)*6
            rd_wr_gz.matrix_basis[0][3] = x + scale + (scale*2)*6
            sc_li_gz.matrix_basis[0][3] = x + scale + (scale*2)*5
            rd_li_gz.matrix_basis[0][3] = x + scale + (scale*2)*5

            dis_gz.matrix_basis[0][3] = x + scale + (scale*2)*7
            cam_gz.matrix_basis[0][3] = x + scale + (scale*2)*8
            al_gz.matrix_basis[0][3] =x + scale + (scale*2)*8

    def space_gizmo(self, type):
        gizmo = self.gizmos.new("GIZMO_GT_button_2d")   #GIZMO_GT_button_2d
        gizmo.target_set_operator("screen.set_camera_viewer_space").type = type
        gizmo.draw_options = {'BACKDROP', 'OUTLINE'}

        # Can also use gz.icon_value to use a custom/generated preview icon.
        if type == 'SOLID':
            icon = 'SHADING_SOLID'
        elif type == 'MATERIAL':
            icon = 'SHADING_TEXTURE'
        elif type == 'RENDERED':
            icon = 'SHADING_RENDERED'
        elif type == 'OVERLAY':
            icon = 'OVERLAY'
        elif type == 'DISABLED':
            icon = 'X'
        elif type == 'CAMERA':
            icon = 'VIEW_CAMERA'
        elif type == 'ALWAYS':
            icon = 'RESTRICT_VIEW_OFF'
        elif type in ('scene_lights','scene_lights_render'):
            icon = 'OUTLINER_OB_LIGHT'
        elif type in ('scene_world', 'scene_world_render'):
            icon = 'WORLD'

        gizmo.icon = icon

        return gizmo

    def draw_space_gizmo(self, context):
        for a in bpy.data.screens[context.screen.name +' Camera Viewer'].areas:
            if a.type == 'VIEW_3D':
                space = a.spaces[0]
                break

        self.space = space

        self.viewer_gizmos['OVERLAY'] = self.space_gizmo('OVERLAY')
        self.viewer_gizmos['SOLID'] = self.space_gizmo('SOLID')
        self.viewer_gizmos['MATERIAL'] = self.space_gizmo('MATERIAL')
        self.viewer_gizmos['RENDERED'] = self.space_gizmo('RENDERED')

        self.viewer_gizmos['DISABLED'] = self.space_gizmo('DISABLED')
        self.viewer_gizmos['CAMERA'] = self.space_gizmo('CAMERA')
        self.viewer_gizmos['ALWAYS'] = self.space_gizmo('ALWAYS')

        self.viewer_gizmos['scene_lights'] = self.space_gizmo('scene_lights')
        self.viewer_gizmos['scene_world'] = self.space_gizmo('scene_world')
        self.viewer_gizmos['scene_lights_render'] = self.space_gizmo('scene_lights_render')
        self.viewer_gizmos['scene_world_render'] = self.space_gizmo('scene_world_render')

    def draw_prepare(self, context):
        camera_viewer = context.screen.camera_viewer
        if not self.space and context.screen.camera_viewer.viewer_toggle:
            self.draw_space_gizmo(context)
        elif self.space:
            x = camera_viewer.x
            y = camera_viewer.y
            region_width = context.region.width
            region_height = context.region.height
            for r in context.area.regions:
                if r.type == 'UI':
                    n_panel = r.width
                    break
            for r in context.area.regions:
                if r.type == 'TOOLS':
                    tool_panel = r.width
                    break
                
            scene = context.scene
            render = scene.render
            scale = render.resolution_y/1080
            width = int(render.resolution_x/scale * camera_viewer.size/3.5)
            height = int(render.resolution_y/scale * camera_viewer.size/3.5)

            self.draw_navigation(context, camera_viewer, x, y, width, height, region_width, region_height, tool_panel, n_panel)

            self.draw_modify(context, camera_viewer, x, y, width, height, region_width, region_height, tool_panel, n_panel)

            self.draw_space(context, camera_viewer, x, y, width, height, region_width, region_height, tool_panel, n_panel)

    def setup(self, context):
        gizmo = self.gizmos.new("GIZMO_GT_button_2d")   #GIZMO_GT_button_2d
        gizmo.draw_options = {'BACKDROP', 'OUTLINE'}
        gizmo.target_set_operator("screen.navigation_camera_viewer")

        gizmo.alpha = 0
        gizmo.alpha_highlight = 0

        gizmo.use_tooltip = True
        gizmo.show_drag = True

        # Can also use gz.icon_value to use a custom/generated preview icon.
        gizmo.icon = 'BLANK1'

        self.viewer_gizmos['Navigation'] = gizmo

        gizmo = self.gizmos.new("GIZMO_GT_button_2d")   #GIZMO_GT_button_2d
        gizmo.target_set_operator("screen.modify_camera_viewer")
        gizmo.draw_options = {'BACKDROP', 'OUTLINE'}

        gizmo.color = 0.0, 0.5, 1.0
        gizmo.alpha = 0.5
        gizmo.backdrop_fill_alpha = 0.7

        gizmo.color_highlight = 1.0, 0.5, 0.0
        gizmo.alpha_highlight = 0.8

        gizmo.use_tooltip = True
        gizmo.line_width = 1
        gizmo.show_drag = True
        gizmo.scale_basis = 12
        gizmo.icon = 'EMPTY_ARROWS'

        if context.screen.camera_viewer.viewer_toggle:
            self.draw_space_gizmo(context)

class Camera_Viewer_Props(bpy.types.PropertyGroup):
    def update_toggle(self, context):
        name = context.screen.name

        if self.viewer_toggle == True:
            # Create a new screen and set it as the active screen
            if not bpy.data.screens.get(name + ' Camera Viewer'):

                bpy.ops.screen.new()

                bpy.data.screens['Default.001'].name = name + ' Camera Viewer'
                
                context.window.screen=bpy.data.screens[name]

                for a in bpy.data.screens[context.screen.name +' Camera Viewer'].areas:
                    if a.type == 'VIEW_3D':
                        space = a.spaces[0]
                        break
                space.overlay.show_look_dev = False

            offscreen = get_offscreen(context)

            dns["draw_viewer_toggle"] = bpy.types.SpaceView3D.draw_handler_add(draw_viewer_toggle, (context, offscreen), 'WINDOW', 'POST_PIXEL')

        elif self.viewer_toggle == False:

            if dns.get("draw_viewer_toggle"):

                bpy.types.SpaceView3D.draw_handler_remove(dns["draw_viewer_toggle"], 'WINDOW')

    def update_quality(self, context):

        if dns.get("draw_viewer_toggle"):

            bpy.types.SpaceView3D.draw_handler_remove(dns["draw_viewer_toggle"], 'WINDOW')

        offscreen = get_offscreen(context)

        dns["draw_viewer_toggle"] = bpy.types.SpaceView3D.draw_handler_add(draw_viewer_toggle, (context, offscreen), 'WINDOW', 'POST_PIXEL')

    lock_camera : bpy.props.BoolProperty(default=False)
    camera : bpy.props.StringProperty(default='Camera')
    active_camera : bpy.props.BoolProperty(default=False)
    viewer_toggle : bpy.props.BoolProperty(default=False, update=update_toggle)
    size : bpy.props.FloatProperty(name = 'References Size', default=1, min = 0.1)
    x : bpy.props.FloatProperty(name = 'References Position X', default=0)
    y : bpy.props.FloatProperty(name = 'References Position Y', default=0)
    border_thickness : bpy.props.IntProperty(name = 'Border Thickness', default=2, min = 0, max = 10)
    border_color: bpy.props.FloatVectorProperty(name="Border Color",
                                                 subtype='COLOR',
                                                 size=4,  # RGBA values
                                                 default=(0.0, 0.0, 0.0, 1.0), min = 0, max = 1)
    quality : bpy.props.FloatProperty(name = 'Quality', default=20, min = 1, max = 100, subtype="PERCENTAGE", update=update_quality)
    show_camera_name : bpy.props.BoolProperty(name = 'Show Camera Name', default=True)
    statuses : bpy.props.StringProperty(name = 'statuses', default='')

    position : bpy.props.EnumProperty(default = "Left-Bottom",
                            items = [('Left-Bottom', 'Left-Bottom', ''),
                                    ('Right-Bottom', 'Right-Bottom', ''),
                                    ('Left-Top', 'Left-Top', ''),
                                    ('Right-Top', 'Right-Top', ''),
                                    ],)

class Camera_Viewer_UI_Props(bpy.types.PropertyGroup):
    use_ui : bpy.props.BoolProperty(default=True)
    use_lighting : bpy.props.BoolProperty(default=True)
    use_compositor : bpy.props.BoolProperty(default=True)

class Rest_Camera_Viewer_OT(bpy.types.Operator):
    bl_idname = "screen.rest_camera_viewer"
    bl_label = "Rest Camera Viewers"
    bl_description = "Rest Camera Viewer"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mode = context.screen.camera_viewer.viewer_toggle

        camera_viewer = context.screen.camera_viewer

        camera_viewer.size = 1
        camera_viewer.x = 0
        camera_viewer.y = 0
        camera_viewer.quality = 20
        camera_viewer.position = 'Left-Bottom'

        context.screen.camera_viewer.viewer_toggle = False
        context.screen.camera_viewer.viewer_toggle = mode

        return {'FINISHED'}
    
class Toggle_Camera_Viewer_OT(bpy.types.Operator):
    bl_idname = "screen.toggle_camera_viewer"
    bl_label = "Toggle Camera Viewers"
    bl_description = "Toggle Camera Viewer"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.screen.camera_viewer.viewer_toggle = not context.screen.camera_viewer.viewer_toggle
        return {'FINISHED'}

class Modify_Camera_Viewer_OT(bpy.types.Operator):
    bl_idname = "screen.modify_camera_viewer"
    bl_label = "Modify Camera Viewer"
    bl_description = "Modify Camera Viewer"
    bl_options = {'REGISTER', 'UNDO'}

    space = None
    current_y = None
    size = None
    quality = None
    _handle = None
    position = None

    @classmethod
    def poll(cls, context):
        return context.screen.camera_viewer.viewer_toggle
    
    def modal(self, context, event):
        context.area.tag_redraw()
        camera_viewer = context.screen.camera_viewer
        space = self.space
        if event.type == 'ONE':
            space.shading.type = 'SOLID'
        elif event.type == 'TWO':
            space.shading.type = 'MATERIAL'
        elif event.type == 'THREE' and context.scene.render.engine != 'CYCLES':
            space.shading.type = 'RENDERED'

        if event.type == 'MOUSEMOVE':
            if event.shift:
                if event.mouse_region_x > context.region.width/3 and event.mouse_region_y < context.region.height/3:
                    camera_viewer.position = 'Right-Bottom'
                elif event.mouse_region_x < context.region.width/3 and event.mouse_region_y < context.region.height/3:
                    camera_viewer.position = 'Left-Bottom'
                elif event.mouse_region_x > context.region.width/3 and event.mouse_region_y > context.region.height - context.region.height/3:
                    camera_viewer.position = 'Right-Top'
                elif event.mouse_region_x < context.region.width/3 and event.mouse_region_y > context.region.height - context.region.height/3:
                    camera_viewer.position = 'Left-Top'

                self.current_y = event.mouse_region_y
            else:
                if 'Bottom' in camera_viewer.position:
                    camera_viewer.size = self.size + ((event.mouse_region_y/self.current_y)-1)*2
                elif 'Top' in camera_viewer.position:
                    camera_viewer.size = self.size + ((event.mouse_region_y/self.current_y)-1)*-2

        elif event.type == 'WHEELUPMOUSE':
            # Handle mouse scroll up events
            if camera_viewer.quality == 1:
                camera_viewer.quality = camera_viewer.quality + 4
            else:
                camera_viewer.quality = camera_viewer.quality + 5
            
        elif event.type == 'WHEELDOWNMOUSE':
            # Handle mouse scroll down events
            camera_viewer.quality = camera_viewer.quality - 5

        elif event.type in {'R'}:
            camera_viewer.quality = 20
        elif event.type in {'S'}:
            camera_viewer.size = 1

        elif event.type == 'LEFTMOUSE':
            camera_viewer.statuses = ''
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            camera_viewer.size = self.size
            camera_viewer.quality = self.quality
            camera_viewer.statuses = ''
            camera_viewer.position = self.position

            return {'CANCELLED'}

        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            camera_viewer = context.screen.camera_viewer
            for a in bpy.data.screens[context.screen.name +' Camera Viewer'].areas:
                if a.type == 'VIEW_3D':
                    space = a.spaces[0]
                    break
            self.space = space
            self.size = camera_viewer.size
            self.quality = camera_viewer.quality
            self.current_y = event.mouse_region_y
            self.position = camera_viewer.position
            camera_viewer.statuses = 'EDIT'
            # The arguments we pass the callback.
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}

class Navigation_Camera_Viewer_OT(bpy.types.Operator):
    bl_idname = "screen.navigation_camera_viewer"
    bl_label = "Navigation Camera Viewer"
    bl_description = "Navigation Camera Viewer"
    bl_options = {'REGISTER', 'UNDO'}

    space = None
    camera = None
    lens = None
    ortho_scale = None
    current_x = None
    current_y = None
    location = None
    rotation_euler = None
    matrix_world = None

    def move_camera_local(self, camera, x, y, z):
        # Convert the local movement deltas to global coordinates
        vec = Vector((x, y, z))
        inv = camera.matrix_world.copy()
        inv.invert()
        # vec aligned to local axis in Blender 2.8+
        # in previous versions: vec_rot = vec * inv
        vec_rot = vec @ inv
        camera.location += vec_rot

    @classmethod
    def poll(cls, context):
        return context.screen.camera_viewer.viewer_toggle

    def modal(self, context, event):
        camera_viewer = context.screen.camera_viewer
        space = self.space
        camera = self.camera
            
        if event.type == 'ONE':
            space.shading.type = 'SOLID'
        elif event.type == 'TWO':
            space.shading.type = 'MATERIAL'
        elif event.type == 'THREE' and context.scene.render.engine != 'CYCLES':
            space.shading.type = 'RENDERED'

        if event.type == 'WHEELUPMOUSE':
            if camera.data.type in {"PERSP",'PANO'}:
                camera.data.lens += 1 if event.shift else 5
            elif camera.data.type == 'ORTHO':
                camera.data.ortho_scale += 1 if event.shift else 5
        elif event.type == 'WHEELDOWNMOUSE':
            if camera.data.type in {"PERSP",'PANO'}:
                camera.data.lens -= 1 if event.shift else 5
            elif camera.data.type == 'ORTHO':
                camera.data.ortho_scale -= 1 if event.shift else 5
        elif event.type == 'MIDDLEMOUSE':
             camera.data.lens = self.lens
             camera.data.ortho_scale = self.ortho_scale

        if event.type in {'W','A','S','D','R','F','E','Q'}:
            if event.shift:
                speed=1
            elif event.alt:
                speed=0.1
            else:
                speed=0.5
            if event.type == 'W':
                self.move_camera_local(camera, 0, 0, speed*-1)
            elif event.type == 'A':
                self.move_camera_local(camera, speed*-1, 0, 0)
            elif event.type == 'S':
                self.move_camera_local(camera, 0, 0, speed)
            elif event.type == 'D':
                self.move_camera_local(camera, speed, 0, 0)
            elif event.type == 'R':
                self.move_camera_local(camera, 0, speed, 0)
            elif event.type == 'F':
                self.move_camera_local(camera, 0, speed*-1, 0)
            elif event.type == "E":
                camera.location[2] = self.location[2] + speed
            elif event.type == "Q":
                camera.location[2] = self.location[2] - speed

        if event.type == 'MOUSEMOVE':
            if event.shift:
                x = (event.mouse_region_x - self.current_x)/(context.region.width)
                y = (event.mouse_region_y - self.current_y)/(context.region.height)
                self.move_camera_local(camera, x, 0, 0)
                camera.location[2] = camera.location[2] + y
            else:
                camera.rotation_euler[0] = self.rotation_euler[0] + (event.mouse_region_y - self.current_y)/(context.region.height*5)
                camera.rotation_euler[2] = self.rotation_euler[2] - (event.mouse_region_x - self.current_x)/(context.region.width*5)

        elif event.type == 'LEFTMOUSE':
            camera_viewer.statuses = ''
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            camera.matrix_world = self.matrix_world
            camera.data.lens = self.lens
            camera.data.ortho_scale = self.ortho_scale
            camera_viewer.statuses = ''
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        camera_viewer = context.screen.camera_viewer

        for a in bpy.data.screens[context.screen.name +' Camera Viewer'].areas:
            if a.type == 'VIEW_3D':
                space = a.spaces[0]
                break
        if not camera_viewer.active_camera:
            if camera_viewer.lock_camera and camera_viewer.camera:
                camera = bpy.data.objects[camera_viewer.camera]
            else:
                camera = context.scene.camera
        else:
            if context.active_object.type == 'CAMERA':
                camera = context.active_object
            else:
                return
            
        self.space = space
        self.camera = camera

        self.matrix_world = camera.matrix_world.copy()
        self.location = camera.location
        self.rotation_euler = camera.rotation_euler
        self.current_x = event.mouse_region_x
        self.current_y = event.mouse_region_y
        self.lens = camera.data.lens
        self.ortho_scale = camera.data.ortho_scale
        camera_viewer.statuses = 'Navigation'

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class Set_Camera_Viewer_Space_OT(bpy.types.Operator):
    bl_idname = "screen.set_camera_viewer_space"
    bl_label = "Set Camera Viewer Space"
    bl_description = "Set Camera Viewer Space"
    bl_options = {'REGISTER', 'UNDO'}

    type : bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        for a in bpy.data.screens[context.screen.name +' Camera Viewer'].areas:
            if a.type == 'VIEW_3D':
                space = a.spaces[0]
                break

        if self.type == 'SOLID':
            space.shading.type = 'SOLID'
        elif self.type == 'SOLID':
            space.shading.type = 'SOLID'
        elif self.type == 'MATERIAL':
            space.shading.type = 'MATERIAL'
        elif self.type == 'RENDERED' and context.scene.render.engine != 'CYCLES':
            space.shading.type = 'RENDERED'
        elif self.type == 'OVERLAY':
            space.overlay.show_overlays = not space.overlay.show_overlays
        elif self.type == 'DISABLED':
            space.shading.use_compositor = 'DISABLED'
        elif self.type == 'CAMERA':
            space.shading.use_compositor = 'CAMERA'
        elif self.type == 'ALWAYS':
            space.shading.use_compositor = 'ALWAYS'
        elif self.type == 'scene_lights':
            space.shading.use_scene_lights = not space.shading.use_scene_lights
        elif self.type == 'scene_world':
            space.shading.use_scene_world = not space.shading.use_scene_world
        elif self.type == 'scene_lights_render':
            space.shading.use_scene_lights_render = not space.shading.use_scene_lights_render
        elif self.type == 'scene_world_render':
            space.shading.use_scene_world_render = not space.shading.use_scene_world_render

        return {'FINISHED'}

class CAMERA_PT_Viewer(bpy.types.Panel):
    bl_idname = "CAMERA_PT_Viewer"
    bl_options = {"DEFAULT_CLOSED"}
    bl_label = "Camera Viewer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 12

    def draw(self, context):
        camera_viewer = context.screen.camera_viewer
        camera_viewer_ui = context.scene.camera_viewer_ui
        for a in bpy.data.screens[context.screen.name +' Camera Viewer'].areas:
            if a.type == 'VIEW_3D':
                space = a.spaces[0]
                break

        layout = self.layout
        layout.label(text='Camera Viewer')

        col = layout.column()
        row = col.row()
        row.prop(camera_viewer, "show_camera_name", text="Show Name")
        row.prop(camera_viewer_ui, "use_ui", text="Use Viewer UI")
        row = col.row()
        row.active = camera_viewer_ui.use_ui
        row.prop(camera_viewer_ui, "use_lighting", text="Lighting")
        row.prop(camera_viewer_ui, "use_compositor", text="Compositor")

        if context.scene.render.engine == 'CYCLES' and space.shading.type in {'RENDERED'}:
            col = layout.column()
            col.alert = True
            col.label(text='Cycles render is not supported', icon = "ERROR")

        layout.operator("screen.rest_camera_viewer", icon = "FILE_REFRESH", text = "Rest Viewer")

        layout.prop(camera_viewer, "active_camera", text="Active Camera Only")

        col = layout.column()

        row = col.row(heading="Lock Camera")
        row.active = not camera_viewer.active_camera
        row.use_property_split = True
        row.use_property_decorate = False
        row.prop(camera_viewer, "lock_camera", text="")
        row = row.row()
        row.enabled = camera_viewer.lock_camera
        row.prop_search(camera_viewer, "camera", bpy.data, 'objects', text="")
        col.prop(camera_viewer, "quality", text="Quality", slider=True)
        col.prop(camera_viewer, "position", text="Position")
        row = col.row(align=True)
        row.prop(camera_viewer, "x", text="X")
        row.prop(camera_viewer, "y", text="Y")
        col.prop(camera_viewer, "size", text="Size")
        col.label(text = 'Border')
        row = col.row()
        row.prop(camera_viewer, "border_thickness", text="Thickness")
        row.prop(camera_viewer, "border_color", text="")

        row = layout.row(heading='Overlays')
        row.prop(space.overlay, "show_overlays", text="", icon ='OVERLAY')

        col = layout.column()
        col.active = space.overlay.show_overlays
        row = col.row()
        row.prop(space.overlay, "show_extras", text="Extra")
        row.prop(space.overlay, "show_bones", text="Bones")
        
        row = col.row()
        row.prop(space.overlay, "show_wireframes", text="Wireframes")

        if space.shading.type in {'MATERIAL'}:
            row.prop(space.overlay, "show_look_dev", text="HDRI Preview")

        row = layout.row(heading='Shading')
        row.prop(space.shading, "type", text="", expand=True)
    
        col = layout.column()
        
        if space.shading.type in {'SOLID'}:
            col.label(text = 'Lighting')
            row = col.row()
            row.prop(space.shading, "light", expand = True)
            if space.shading.light == 'STUDIO':
                prefs = context.preferences
                system = prefs.system
                row = col.row()
                if not system.use_studio_light_edit:
                    row.scale_y = 0.6  # Smaller studio-light preview.
                    row.template_icon_view(space.shading, "studio_light", scale_popup=3.0)
                else:
                    row.prop(
                        system,
                        "use_studio_light_edit",
                        text="Disable Studio Light Edit",
                        icon='NONE',
                        toggle=True,
                    )
            elif space.shading.light == 'MATCAP':
                row = col.row()
                row.scale_y = 0.6
                row.template_icon_view(space.shading, "studio_light", scale_popup=3.0)

        if space.shading.type in {'WIREFRAME', 'SOLID'}:
            
            col.label(text = 'Wire Color')
            col.row().prop(space.shading, "wireframe_color_type", expand=True)

        if space.shading.type in {'SOLID'}:

            col.label(text = 'Color')
            col.grid_flow(columns=3, align=True).prop(space.shading, "color_type", expand=True)

            col.label(text = 'Background')
            col.row().prop(space.shading, "background_type", expand=True)
            if space.shading.background_type == 'VIEWPORT':
                col.prop(space.shading, "background_color", text='')

            col.label(text = 'Options')
            row = col.row(align=True)
            row.prop(space.shading, 'show_xray', text='')
            sub = row.row()
            sub.active = space.shading.show_xray
            sub.prop(space.shading, 'xray_alpha', text='X-Ray')
            
            row = col.row(align=True)
            row.prop(space.shading, "show_shadows", text="")
            row.active = not space.shading.show_xray
            sub = row.row(align=True)
            sub.active = space.shading.show_shadows
            sub.prop(space.shading, "shadow_intensity", text="Shadow")
            sub.popover(
                panel="VIEW3D_PT_shading_options_shadow",
                icon='PREFERENCES',
                text="",
            )

            col.prop(space.shading, "use_dof")

        if space.shading.type in {'WIREFRAME', 'SOLID'}:

            row = col.row()
            row.prop(space.shading, "show_object_outline")
            row.prop(space.shading, "object_outline_color", text= '')

        if space.shading.type in {'MATERIAL', 'RENDERED'}:
            col.label(text = 'Lighting')
            if space.shading.type in {'MATERIAL'}:
                col = layout.column()
                col.prop(space.shading, "use_scene_lights")
                col.prop(space.shading, "use_scene_world")
            if space.shading.type in {'RENDERED'}:
                col = layout.column()
                col.prop(space.shading, "use_scene_lights_render")
                col.prop(space.shading, "use_scene_world_render")
            col.label(text = 'Render Pass')
            col.prop(space.shading, "render_pass", text='')
            col.separator()
            col.row().prop(space.shading, "use_compositor", expand=True)

class CAMERA_VIEWER_OT_AddHotkey(bpy.types.Operator):
    ''' Add hotkey entry '''
    bl_idname = "camera_viewer.add_hotkey"
    bl_label = "Add Hotkey"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        add_hotkey()
        return {'FINISHED'}

def camera_viewer_header(self, context):
    camera_viewer = context.screen.camera_viewer
    layout = self.layout
    row = layout.row(align=True)
    row.prop(camera_viewer, "viewer_toggle", icon='VIEW_CAMERA' if camera_viewer.viewer_toggle else 'VIEW_CAMERA_UNSELECTED', text="")
    sub = row.row(align=True)
    sub.enabled = bool(bpy.data.screens.get(context.screen.name +' Camera Viewer'))
    sub.popover(panel="CAMERA_PT_Viewer", text="")

def add_hotkey():

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        ################################################

        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new('screen.toggle_camera_viewer', 'F1', 'PRESS',alt=True)
        kmi.active = True
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new('screen.modify_camera_viewer', 'F1', 'PRESS')
        kmi.active = True
        addon_keymaps.append((km, kmi))

def remove_hotkey():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    keymaps_to_remove = ['3D View']

    for keymap_name in keymaps_to_remove:
        keymap = kc.keymaps.get(keymap_name)
        if keymap:
            keymap_items = [kmi for kmi in keymap.keymap_items if kmi in addon_keymaps]
            for kmi in keymap_items:
                keymap.keymap_items.remove(kmi)
            kc.keymaps.remove(keymap)

    addon_keymaps.clear()

addon_keymaps = []

classes = (
     Camera_Viewer_Props,
     Camera_Viewer_UI_Props,
     Camera_Viewer_UI_Control,
     CAMERA_PT_Viewer,
     Modify_Camera_Viewer_OT,
     Navigation_Camera_Viewer_OT,
     Rest_Camera_Viewer_OT,
     Set_Camera_Viewer_Space_OT,
     Toggle_Camera_Viewer_OT,
     CAMERA_VIEWER_OT_AddHotkey,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Screen.camera_viewer = bpy.props.PointerProperty(type = Camera_Viewer_Props)

    bpy.types.Scene.camera_viewer_ui = bpy.props.PointerProperty(type = Camera_Viewer_UI_Props)

    bpy.types.VIEW3D_HT_header.append(camera_viewer_header)

    bpy.app.handlers.load_post.append(check_viewer_property)

    dns["draw_viewport_outline"] = bpy.types.SpaceView3D.draw_handler_add(draw_viewport_outline, (), 'WINDOW', 'POST_PIXEL')

    add_hotkey()

def unregister():
    remove_hotkey()

    if dns.get("draw_viewport_outline"):

        bpy.types.SpaceView3D.draw_handler_remove(dns["draw_viewport_outline"], 'WINDOW')

    if dns.get("draw_viewer_toggle"):

        bpy.types.SpaceView3D.draw_handler_remove(dns["draw_viewer_toggle"], 'WINDOW')

    bpy.types.VIEW3D_HT_header.remove(camera_viewer_header)

    del bpy.types.Scene.camera_viewer_ui

    del bpy.types.Screen.camera_viewer
    
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

