bl_info = {
	"name": "TexTools Bake",
	"description": "Texture baking and Color ID tools, based on TexTools.",
	"author": "Gabo Salcedo; original TexTools by renderhjs, franMarz, Sav Martin",
	"version": (1, 0, 0),
	"blender": (4, 2, 0),
	"category": "Render",
	"location": "Image Editor > Sidebar > 'TexTools Bake' tab",
	"doc_url": "https://github.com/Patituerto/TexTools-Blender/tree/textools-bake",
}

# TexTools Bake is a community fork of TexTools (https://github.com/franMarz/TexTools-Blender)
# that keeps only the Baking and Color ID tools, updated for Blender 5.
# Licensed under the GNU GPL v3 or later, like the original. See LICENSE.txt.


from . import settings
from . import utilities_ui
from . import utilities_bake
from . import utilities_color

from . import op_bake
from . import op_bake_explode
from . import op_bake_organize_names
from . import op_texture_preview
from . import op_texture_preview_cleanup
from . import op_texture_save
from . import op_texture_open
from . import op_texture_select
from . import op_texture_remove
from . import op_color_assign
from . import op_color_clear
from . import op_color_convert_texture
from . import op_color_convert_vertex_colors
from . import op_color_from_elements
from . import op_color_from_materials
from . import op_color_from_directions
from . import op_color_io_export
from . import op_color_io_import
from . import op_color_select
from . import op_color_select_vertex


import bpy
import math

from bpy.types import Menu, Operator, Panel, AddonPreferences, PropertyGroup
from bpy.props import (
	StringProperty,
	BoolProperty,
	IntProperty,
	IntVectorProperty,
	FloatProperty,
	FloatVectorProperty,
	EnumProperty,
	PointerProperty,
)

from .settings import tt_settings, prefs


def icon_get(name):
	return utilities_ui.icon_get(name)


def on_bake_def_back_color_set(self, context):
	if self.bool_bake_back_color:
		tt_settings().bake_back_color = self.bake_back_color_def


def on_bake_color_space_set(self, context):
	if utilities_ui.set_bake_color_space_int(utilities_ui.get_bake_mode()) == 1:
		tt_settings().bake_color_space = 'Non-Color'
	elif utilities_ui.set_bake_color_space_int(utilities_ui.get_bake_mode()) == 0:
		tt_settings().bake_color_space = 'sRGB'
	elif utilities_ui.set_bake_color_space_int(utilities_ui.get_bake_mode()) == 3:
		tt_settings().bake_color_space = 'Utility - Linear - sRGB'
	else:
		tt_settings().bake_color_space = 'Utility - sRGB - Texture'


class Panel_Preferences(AddonPreferences):
	bl_idname = __package__

	# Addon Preferences https://docs.blender.org/api/blender_python_api_2_67_release/bpy.types.AddonPreferences.html
	swizzle_y_coordinate: EnumProperty(items=
		(
			('Y+', 'Y+ OpenGL', 'Used in Blender, Maya, Modo, Toolbag, Unity'), 
			('Y-', 'Y- Direct X', 'Used in 3ds Max, CryENGINE, Source, Unreal Engine')
		),
		description="Color template",
		name="Swizzle Coordinates",
		default='Y+'
	)
	bake_device: EnumProperty(items=
		[	
			('DEFAULT', 'Default', 'Use the device specified in the Render Properties panel'), 
			('CPU', 'CPU', 'Always use the CPU when baking with Cycles'), 
			('GPU', 'GPU', 'Always use the GPU when baking with Cycles')
		], 
		description="Temporary device override only for baking", 
		name="Baking Device",
		default='DEFAULT'
	)
	bake_32bit_float: EnumProperty(items=
		(
			('8', '8 Bit', ''), 
			('32', '32 Bit', '')
		),
		description="", 
		name="Image depth",
		default='8'
	)
	bake_back_color_def: FloatVectorProperty(
		name="Global custom baking background color", 
		subtype='COLOR', 
		size=4, 
		min=0, max=1, 
		default=(0.0, 0.0, 0.0, 1.0), 
		update = on_bake_def_back_color_set
	)
	bool_bake_back_color: EnumProperty(items=
		[	
			('DEFAULT', 'Default', 'Use default TexTools background colors for baked textures'), 
			('CUSTOM', 'Custom', 'Set a global custom RGBA color for the background. Note that a transparent background can be specified')
		], 
		description="Mode for baked textures background color and alpha", 
		name="Bake background",
		default='DEFAULT',
		update=on_bake_def_back_color_set
	)
	bake_color_space_def: EnumProperty(items=
		[	
			('STANDARD', 'Standard', 'Set sRGB as Color Space for all baked textures except for Normal maps'), 
			('PBR', 'PBR typical', 'Set Linear as Color Space for all baked maps except for Diffuse/Base Color, SSS/Emission color, colored Transmission, Environment, Combined or any custom Mode'),
			('ASTANDARD', 'ACES standard', 'Set ACES sRGB Texture as Color Space for all baked textures except for Normal maps'), 
			('APBR', 'ACES PBR typical', 'Set ACES Linear sRGB as Color Space for all baked maps except for Diffuse/Base Color, SSS/Emission color, colored Transmission, Environment, Combined or any custom Mode')
		], 
		description="Automatically set the Color Space of the baked images. Can be changed in the Baking panel", 
		name="Bake Color Space",
		default='STANDARD',
		update=on_bake_color_space_set
	)
	bool_alpha_ignore: BoolProperty(
		name="Ignore Alpha when baking other modes", 
		default=True
	)
	bool_emission_ignore: BoolProperty(
		name="Ignore Emission Strength when baking Emission", 
		default=True
	)
	bool_clean_transmission: BoolProperty(
		name="Ignore other channels when baking Transmission", 
		default=False
	)
	bool_color_id_vertex_color_gamma: BoolProperty(
		name="Apply gamma to ID Colors in Vextex Color mode for visual consistency", 
		default=False
	)
	bool_modifier_auto_high: BoolProperty(
		name="Detect Objects with Subdiv or Bevel Mods as a Highpoly pair for baking", 
		default=True
	)
	bake_mode_panel_scale: FloatProperty(
		name="Bake Mode Panel Scale", 
		description="Scale of the bake mode selector panel icons", 
		default=3.6, 
		min=2, 
		max=10
	)
	bool_help: BoolProperty(
		name="Show help buttons on panels", 
		default=True
	)


	def draw(self, context):
		layout = self.layout

		box = layout.box()
		col = box.column(align=True)
		col.prop(self, "bake_device", icon='PREFERENCES')
		if self.bake_device == 'DEFAULT':
			col.label(text="Use the device specified in the Render Properties panel.")
		elif self.bake_device == 'CPU':
			col.label(text="Always use the CPU when baking in TexTools with Cycles.")
		elif self.bake_device == 'GPU':
			col.label(text="Always use the GPU when baking in TexTools with Cycles.")

		box.separator()
		col = box.column(align=True)
		col.prop(self, "swizzle_y_coordinate", icon='ORIENTATION_GLOBAL')
		if self.swizzle_y_coordinate == 'Y+':
			col.label(text="Y+ used in: Blender, Maya, Modo, Toolbag, Unity")
		elif self.swizzle_y_coordinate == 'Y-':
			col.label(text="Y- used in: 3ds Max, CryENGINE, Source, Unreal Engine")

		box.separator()
		col = box.column(align=True)
		col.prop(self, "bake_32bit_float", icon='IMAGE_RGB')
		if self.bake_32bit_float == '8':
			col.label(text="8 Bit images are used. Banding may appear in normal maps.")
		elif self.bake_32bit_float == '32':
			col.label(text="32 Bit images are used. Images may require dithering to 8 bit.")

		box.separator()
		col = box.column(align=True)
		col.prop(self, "bake_color_space_def", icon='IMAGE_ZDEPTH')
		if self.bake_device == 'STANDARD':
			col.label(text="Set sRGB as Color Space for all baked textures except for Normal maps.")
		elif self.bake_device == 'PBR':
			col.label(text="Set Linear as Color Space for all baked maps except for Diffuse/Base Color, SSS/Emission color, colored Transmission, Environment, Combined or any custom Mode.")
		elif self.bake_device == 'ASTANDARD':
			col.label(text="Set ACES sRGB Texture as Color Space for all baked textures except for Normal maps.")
		elif self.bake_device == 'APBR':
			col.label(text="Set ACES Linear sRGB as Color Space for all baked maps except for Diffuse/Base Color, SSS/Emission color, colored Transmission, Environment, Combined or any custom Mode.")
	
		box.separator()
		col = box.column(align=True)
		col.prop(self, "bool_bake_back_color", icon='IMAGE_RGB_ALPHA')
		if self.bool_bake_back_color == 'CUSTOM':
			col.prop(self, "bake_back_color_def", text ="")

		box.separator()
		col = box.column(align=True)
		col.prop(self, "bool_modifier_auto_high", icon='MESH_MONKEY')

		box.separator()
		col = box.column(align=True)
		col.prop(self, "bool_alpha_ignore", icon='ANIM')
		col.prop(self, "bool_clean_transmission", icon='ANIM')
		col.prop(self, "bool_emission_ignore", icon='ANIM')
		col.prop(self, "bake_mode_panel_scale")

		box.separator()
		col = box.column(align=True)
		col.prop(self, "bool_color_id_vertex_color_gamma", icon='INDIRECT_ONLY_ON')

		box.separator()
		col = box.column(align=True)
		col.prop(self, "bool_help", icon='INFO')


		box = layout.box()
		box.label(text="Links")
		col = box.column(align=True)
		col.operator("wm.url_open", text="TexTools (original project)", icon='URL').url = "https://github.com/franMarz/TexTools-Blender"



		box = layout.box()

		box.label(text="Additional Links")
		col = box.column(align=True)
		col.operator("wm.url_open", text="Donate", icon='HELP').url = "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=ZC9X4LE7CPQN6"
		col.operator("wm.url_open", text="GIT Code", icon='WORDWRAP_ON').url = "https://github.com/SavMartin/TexTools-Blender"
		
		col.label(text="Discussions")
		row = col.row(align=True)
		row.operator("wm.url_open", text="BlenderArtists", icon='BLENDER').url = "https://blenderartists.org/forum/showthread.php?443182-TexTools-for-Blender"
		row.operator("wm.url_open", text="Polycount").url = "http://polycount.com/discussion/197226/textools-for-blender"
		row.operator("wm.url_open", text="Twitter").url = "https://twitter.com/search?q=%23textools"
		




class UV_OT_op_select_bake_set(Operator):
	bl_idname = "uv.ttbake_select_bake_set"
	bl_label = "Select"
	bl_description = "Select this bake set in scene"

	select_set : StringProperty(default="")

	@classmethod
	def poll(cls, context):
		return True

	def execute(self, context):
		premode = bpy.context.active_object.mode
		if self.select_set != "":
			for bset in settings.sets:
				if bset.name == self.select_set:
					bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
					bpy.ops.object.select_all(action='DESELECT')
					for obj in bset.objects_low:
						obj.select_set(True)
					for obj in bset.objects_high:
						obj.select_set(True)
					for obj in bset.objects_cage:
						obj.select_set(True)
					# Set active object to low poly to better visualize high and low wireframe color
					if bset.objects_low:
						bpy.context.view_layer.objects.active = bset.objects_low[0]
					break
			bpy.ops.object.mode_set(mode=premode)

		return {'FINISHED'}



class UV_OT_op_select_bake_type(Operator):
	bl_idname = "uv.ttbake_select_bake_type"
	bl_label = "Select"
	bl_description = "Select bake objects of this type"

	select_type: StringProperty(default='low')

	@classmethod
	def poll(cls, context):
		return True

	def execute(self, context):
		objects = []
		for bset in settings.sets:
			if self.select_type == 'low':
				objects += bset.objects_low
			elif self.select_type == 'high':
				objects += bset.objects_high
			elif self.select_type == 'cage':
				objects += bset.objects_cage
			elif self.select_type == 'float':
				objects += bset.objects_float
			elif self.select_type == 'issue' and bset.has_issues:
				objects += bset.objects_low
				objects += bset.objects_high
				objects += bset.objects_cage
				objects += bset.objects_float

		if objects:
			premode = bpy.context.active_object.mode
			bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
			bpy.ops.object.select_all(action='DESELECT')
			for obj in objects:
				obj.select_set(True)
			bpy.ops.object.mode_set(mode=premode)

		return {'FINISHED'}



def on_dropdown_size(self, context):
	# Help: http://elfnor.com/drop-down-and-button-select-menus-for-blender-operator-add-ons.html
	size = int(tt_settings().size_dropdown)
	tt_settings().size = size, size

	if size <= 256:
		tt_settings().padding = 2
	else:
		tt_settings().padding = 4





def on_dropdown_size(self, context):
	size = int(tt_settings().size_dropdown)
	tt_settings().size = size, size

	if size <= 256:
		tt_settings().padding = 2
	else:
		tt_settings().padding = 4





def on_color_changed(self, context):
	if tt_settings().color_assign_mode == 'MATERIALS':
		for i in range(0, tt_settings().color_ID_count):
			utilities_color.assign_color(i)



def on_color_dropdown_template(self, context):
	hex_colors = tt_settings().color_ID_templates.split(',')
	tt_settings().color_ID_count = len(hex_colors)

	for i in range(0, len(hex_colors)):
		color = utilities_color.hex_to_color("#"+hex_colors[i])
		utilities_color.set_color(i, color)
	
	if tt_settings().color_assign_mode == 'MATERIALS':
		utilities_color.assign_color(i)



def on_color_count_changed(self, context):
	if bpy.context.active_object and tt_settings().color_assign_mode == 'MATERIALS':
		utilities_color.validate_face_colors(bpy.context.active_object)



def on_color_mode_change(self, context):
	if tt_settings().color_assign_mode == 'MATERIALS':
		# Refresh color palette of existing colored materials
		for i in range(0, tt_settings().color_ID_count):
			utilities_color.assign_color(i)
	if bpy.context.active_object is not None:
		if bpy.context.active_object.mode != 'EDIT' and bpy.context.active_object.mode != 'OBJECT':
			bpy.ops.object.mode_set(mode='OBJECT')
	utilities_color.update_properties_tab()
	utilities_color.update_view_mode()





class TexToolsBakeSettings(PropertyGroup):

	def get_bake_back_color(self):
		return self.get("bake_back_color", bpy.context.preferences.addons[__package__].preferences.bake_back_color_def)

	def set_bake_back_color(self, value):
		if value is not None:
			self["bake_back_color"] = value

	def get_bake_color_space(self):
		return self.get("bake_color_space", utilities_ui.set_bake_color_space_int(utilities_ui.get_bake_mode()))

	def set_bake_color_space(self, value):
		if value is not None:
			self["bake_color_space"] = value


	#Width and Height
	size : IntVectorProperty(
		name = "Size", 
		size=2, 
		description="Texture & UV size in pixels", 
		default = (512,512), 
		subtype = "XYZ"
	)
	size_dropdown : EnumProperty(
		items = utilities_ui.size_textures, 
		name = "Texture Size", 
		update = on_dropdown_size, 
		default = '512'
	)
	padding : IntProperty(
		name = "Padding",
		description = "Padding size in pixels",
		default = 4,
		min = 0,
		max = 256
	)
	bake_samples : IntProperty(
		name = "Samples",
		description = "Samples in Cycles for baking. The higher, the less noise. Use with caution with high values",
		default = 8,
		min = 1,
		max = 4000
	)
	bake_curvature_size : IntProperty(
		name = "Curvature",
		description = "Curvature offset in pixels to process",
		default = 1,
		min = 1,
		max = 64
	)
	bake_wireframe_size : FloatProperty(
		name = "Thickness",
		description = "Wireframe thickness in pixels",
		default = 1,
		min = 0.1,
		max = 4.0
	)
	bake_bevel_size : FloatProperty(
		name = "Radius",
		description = "Bevel radius",
		default = 0.05,
		min = 0.0,
		max = 16
	)
	bake_bevel_samples : IntProperty(
		name = "Bevel Samples",
		description = "Bevel samples. The higher, the less noise. Use with caution with values higher than 64",
		default = 16,
		min = 1,
		max = 256
	)
	bake_thickness_distance : FloatProperty(
		name = "Distance",
		description = "AO distance",
		default = 1.0,
		min = 0.0,
		max = 16.0
	)
	bake_thickness_contrast : FloatProperty(
		name = "Contrast",
		description = "AO contrast",
		default = 1.0,
		min = 0.0,
		max = 2.0
	)
	bake_thickness_local : BoolProperty(
		name = "Only Local",
		description = "Only detect occlusion from the object itself, and not others",
		default = True
	)
	bake_ray_distance : FloatProperty(
		name = "Ray Distance",
		description = "The maximum ray distance for matching points between the active and selected objects. If zero, there is no limit",
		default = 0.00,
		min = 0.000,
		max = 100.00
	)
	bake_cage_extrusion : FloatProperty(
		name = "Cage Extrusion",
		description = "Cage Extrusion, Inflate the cage object by the specified distance for baking",
		default = 0.00,
		min = 0.000,
		max = 100.00
	)
	bake_force : EnumProperty(items= 
		[('None', 'Normal', 'Use the default TexTools baking behaviour'), 
		('Single', 'Single', 'Force a single texture bake across all selected Objects'), 
		('Multi', 'Multi', 'Force a texture bake for each selected Mesh Object by disabling automatic pairing by name')], name = "Force", default = 'None'
	)
	bake_sampling : EnumProperty(items= 
		[('1', 'None', 'No Anti Aliasing (Fast)'), 
		('2', '2x', 'Render 2x and downsample'), 
		('4', '4x', 'Render 2x and downsample')], name = "AA", default = '1'
	)
	# Default Color Space have to be Linear as the first bake mode loaded in the UI before refreshing the bake mode is Tangent Normal
	bake_color_space : EnumProperty(items= 
		[('sRGB', 'sRGB', 'Standard RGB output color space for the baked texture'), 
		('Non-Color', 'Linear', 'Linear or Non-Color output color space for the baked texture'),
		('Utility - sRGB - Texture', 'Utility - sRGB - Texture', 'ACES Standard RGB Texture output color space for the baked texture'), 
		('Utility - Linear - sRGB', 'Utility - Linear - sRGB', 'ACES Linear Standard RGB output color space for the baked texture')], 
		name = "CS", 
		default = 'Non-Color', 
		get = get_bake_color_space, 
		set = set_bake_color_space
	)
	bake_back_color : FloatVectorProperty( 
		description = "Baked texture background color", 
		name = "BK", 
		subtype = 'COLOR', 
		size = 4, 
		min = 0, 
		max = 1, 
		default = (0.0, 0.0, 0.0, 1.0), 
		get = get_bake_back_color, 
		set = set_bake_back_color
	)
	bake_freeze_selection : BoolProperty(
		name="Lock",
		description="Lock baking sets, don't change with selection",
		default = False
	)
	vertex_color_threshold : FloatProperty(
		name = "Vertex Color Threshold",
		description = "Color threshold for vertex color selection",
		default = .01,
		min = 0.0,
		max = 0.5,
		precision=3,
		step=1
	)

	def get_color(hex = "808080"):
		return FloatVectorProperty(
			name="Color1", 
			description="Set Color 1 for the Palette", 
			subtype="COLOR", 
			default=utilities_color.hex_to_color(hex), 
			size=3, 
			max=1.0, min=0.0,
			update=on_color_changed
		)

	# 10 Color ID's
	color_ID_color_0 : get_color(hex="#ff0000")
	color_ID_color_1 : get_color(hex="#0000ff")
	color_ID_color_2 : get_color(hex="#00ff00")
	color_ID_color_3 : get_color(hex="#ffff00")
	color_ID_color_4 : get_color(hex="#00ffff")
	color_ID_color_5 : get_color()
	color_ID_color_6 : get_color()
	color_ID_color_7 : get_color()
	color_ID_color_8 : get_color()
	color_ID_color_9 : get_color()
	color_ID_color_10 : get_color()
	color_ID_color_11 : get_color()
	color_ID_color_12 : get_color()
	color_ID_color_13 : get_color()
	color_ID_color_14 : get_color()
	color_ID_color_15 : get_color()
	color_ID_color_16 : get_color()
	color_ID_color_17 : get_color()
	color_ID_color_18 : get_color()
	color_ID_color_19 : get_color()

	color_ID_templates : EnumProperty(items= 
		[	
			('3d3d3d,7f7f7f,b8b8b8,ffffff', '4 Gray', '...'), 
			('003153,345d4b,688a42,9db63a,d1e231', '5 Greens', '...'),
			('ff0000,0000ff,00ff00,ffff00,00ffff', '5 Code', '...'),
			('3a4342,2e302f,242325,d5cc9e,d6412b', '5 Sea Wolf', '...'),
			('7f87a0,2d3449,000000,ffffff,f99c21', '5 Mustang', '...'),
			('143240,209d8c,fed761,ffab56,fb6941', '5 Sunset', '...'), 
			('0087ed,23ca7a,eceb1d,e37a29,da1c2c', '5 Heat', '...'), 
			('9e00af,7026b9,4f44b5,478bf4,39b7d5,229587,47b151,9dcf46,f7f235,f7b824,f95f1e,c5513c,78574a,4d4b4b,9d9d9d', '15 Rainbow', '...')
		], 
		description="Color template",
		name = "Preset", 
		update = on_color_dropdown_template,
		default = 'ff0000,0000ff,00ff00,ffff00,00ffff'
	)

	color_ID_count : IntProperty(
		name = "Count",
		description="Number of color IDs",
		default = 5,
		update = on_color_count_changed,
		min = 2,
		max = 20
	)

	color_assign_mode : EnumProperty(items= 
		[('MATERIALS', 'Materials', 'Assign simple colored materials to objects or selected faces'), 
		('VERTEXCOLORS', 'Vertex Colors', 'Assign colors as Vertex Colors to objects or selected faces')], 
		name = "Assign Mode", 
		default = 'MATERIALS', 
		update = on_color_mode_change
	)

	# bake_do_save = BoolProperty(
	# 	name="Save",
	# 	description="Save the baked texture?",
	# 	default = False)





class TTBAKE_PT_bake(Panel):
	bl_label = " "
	bl_space_type = 'IMAGE_EDITOR'
	bl_region_type = 'UI'
	bl_category = "TexTools Bake"
	bl_options = {'DEFAULT_CLOSED'}

	def draw_header(self, _):
		layout = self.layout
		row = layout.row(align=True)
		if bpy.context.preferences.addons[__package__].preferences.bool_help:
			row.operator("wm.url_open", text="", icon='INFO').url = "http://renderhjs.net/textools/blender/index.html#texturebaking"
		row.label(text ="Baking")

	def draw(self, context):
		layout = self.layout
		preferences = prefs()
		
		#----------- Texture size -------------
		col = layout.column(align=True)
		col.prop(tt_settings(), "size_dropdown", text="Size")
		col.prop(tt_settings(), "size", text="")
		col.prop(tt_settings(), "padding", text="Padding")
		layout.separator()

		#----------- Baking -------------
		row = layout.row()
		box = row.box()
		col = box.column(align=True)

		if not (tt_settings().bake_freeze_selection and len(settings.sets) > 0):
			# Update sets
			settings.sets = utilities_bake.get_bake_sets()


		# Bake Button
		count = 0
		if tt_settings().bake_force == "Single" and len(settings.sets) > 0:
			count = 1
		else:
			count = len(settings.sets)
		
		row = col.row(align=True)
		row.scale_y = 1.75
		row.operator(op_bake.op.bl_idname, text=f'Bake {count}x', icon_value=icon_get('op_bake'))

		bake_mode = utilities_ui.get_bake_mode()

		# Warning on material or Principled BSDF node need
		if settings.bake_error != "":
			col.label(text=settings.bake_error, icon='ERROR')

		col.separator()
		col_tr = col.column(align=True)
		row = col_tr.row(align=True)
		col = row.column(align=True)

		col.label(text="AA:")
		col.label(text="CS:")
		if preferences.bool_bake_back_color == 'CUSTOM':
			col.label(text="BG:")

		col = row.column(align=True)
		col.scale_x = 1.75

		# anti aliasing
		col.prop(tt_settings(), "bake_sampling", text="", icon_value =icon_get("bake_anti_alias"))
		
		# Color Space selector
		col.prop(tt_settings(), "bake_color_space", text="", icon_value =icon_get("bake_color_space"))

		# Background Color Picker
		if preferences.bool_bake_back_color == 'CUSTOM':
			col.prop(tt_settings(), "bake_back_color", text="")
		
		col = box.column(align=True)

		# Collected Related Textures
		if settings.bversion >= 3.0:
			row = col.row(align=True)
			row.scale_y = 1.5
			row.operator(op_texture_preview.op.bl_idname, text = "Preview Texture", icon_value = icon_get("op_texture_preview"))
			row.operator(op_texture_preview_cleanup.op.bl_idname, text = "", icon = 'TRASH')

		images = utilities_bake.get_baked_images(settings.sets)

		if len(images) > 0:

			image_background = None
			for area in bpy.context.screen.areas:
				if area.ui_type == 'UV':
					if area.spaces[0].image:
						image_background = area.spaces[0].image
						break

			box = col.box()
			# box.label(text="{}x images".format(len(images)), icon="IMAGE_DATA")
			col_box = box.column(align=True)
			for image in images:
				row = col_box.row(align=True)

				# row.label(text=image.name, icon='')
				icon = 'RADIOBUT_OFF'
				if image == image_background:
					icon = 'RADIOBUT_ON'
				row.operator(op_texture_select.op.bl_idname, text=image.name, icon=icon).name = image.name
	
				row = row.row(align=True)
				row.alignment = 'RIGHT'
				if image.filepath != "":
					row.operator(op_texture_open.op.bl_idname, text="", icon_value=icon_get("op_texture_open") ).name = image.name
				else:
					if bpy.app.debug_value != 0:
						row.operator(op_texture_save.op.bl_idname, text="", icon_value=icon_get("op_texture_save") ).name = image.name
					else:
						pass
				
				row.operator(op_texture_remove.op.bl_idname, text="", icon='X' ).name = image.name

				
			col.separator()


		# Bake Mode
		col.template_icon_view(bpy.context.scene, "TTB_bake_mode", scale=5.0, scale_popup=preferences.bake_mode_panel_scale)

		if bpy.app.debug_value != 0:
			row = col.row()
			row.label(text=f"--> Mode: '{bpy.context.scene.TTB_bake_mode}'")

		# Warning: Wrong bake mode, require 
		if bake_mode == 'diffuse':
			if bpy.context.scene.render.engine != 'CYCLES':
				if bpy.context.scene.render.engine != op_bake.modes[bake_mode].engine:
					col.label(text=f"Requires '{op_bake.modes[bake_mode].engine}'", icon='ERROR')

		# Optional Parameters
		col.separator()
		for bset in settings.sets:
			if len(bset.objects_high) > 0 and len(bset.objects_low) > 0:
				col.prop(tt_settings(), "bake_cage_extrusion")
				if settings.bversion >= 2.90:
					col.prop(tt_settings(), "bake_ray_distance")
				break

		# Display Bake mode properties / parameters
		if bake_mode in op_bake.modes:
			if bake_mode == 'combined':
				bake_settings = bpy.context.scene.render.bake
				col.prop(tt_settings(), "bake_samples")
				col.label(text="Lighting:")
				col.prop(bake_settings, "use_pass_direct")
				col.prop(bake_settings, "use_pass_indirect")
				col.label(text="Contributions:")
				col.prop(bake_settings, "use_pass_diffuse")
				col.prop(bake_settings, "use_pass_glossy")
				col.prop(bake_settings, "use_pass_transmission")
				if settings.bversion < 3:
					col.prop(bake_settings, "use_pass_ambient_occlusion")
				col.prop(bake_settings, "use_pass_emit")
			else:
				params = op_bake.modes[bake_mode].params
				if len(params) > 0:
					for param in params:
						col.prop(tt_settings(), param)

		# Warning about projection requirement
		if op_bake.modes[bake_mode].use_project == True and len(settings.sets) > 0:
			if len(settings.sets[0].objects_high) == 0 or len(settings.sets[0].objects_low) == 0:
				col.label(text="Need high and low;", icon='ERROR')
				row = col.row()
				row.label(text="       use suffixes as _hp, _lp")


		box = layout.box()
		col = box.column(align=True)
		
		# Select by type
		if len(settings.sets) > 0:
			row = col.row(align=True)
			row.active = len(settings.sets) > 0

			count_types = {
				'low':0, 'high':0, 'cage':0, 'float':0, 'issue':0, 
			}
			for bset in settings.sets:
				if bset.has_issues:
					count_types['issue']+=1
				if len(bset.objects_low) > 0:
					count_types['low']+=1
				if len(bset.objects_high) > 0:
					count_types['high']+=1
				if len(bset.objects_cage) > 0:
					count_types['cage']+=1
				if len(bset.objects_float) > 0:
					count_types['float']+=1

			# Freeze Selection
			c = row.column(align=True)
			c.active = len(settings.sets) > 0 or tt_settings().bake_freeze_selection
			icon = 'LOCKED' if tt_settings().bake_freeze_selection else 'UNLOCKED'
			c.prop(tt_settings(), "bake_freeze_selection", text=f'Lock {len(settings.sets)}x', icon=icon)

			# Select by type
			if count_types['issue'] > 0:
				row.operator("uv.ttbake_select_bake_type", text='', icon='ERROR').select_type = 'issue'

			row.operator("uv.ttbake_select_bake_type", text='', icon_value=icon_get("bake_obj_low")).select_type = 'low'
			row.operator("uv.ttbake_select_bake_type", text='', icon_value=icon_get("bake_obj_high")).select_type = 'high'
			
			if count_types['float'] > 0:
				row.operator("uv.ttbake_select_bake_type", text='', icon_value=icon_get("bake_obj_float")).select_type = 'float'
			
			if count_types['cage'] > 0:
				row.operator("uv.ttbake_select_bake_type", text='', icon_value=icon_get("bake_obj_cage")).select_type = 'cage'

			# List bake sets
			box2 = box.box()
			row = box2.row()
			split = None

			countTypes = (0 if count_types['low'] == 0 else 1) + (0 if count_types['high'] == 0 else 1) + (0 if count_types['cage'] == 0 else 1) + (0 if count_types['float'] == 0 else 1)
			if countTypes > 2:
				# More than 3 types, use less space for label
				split = row.split(factor=0.45)
			else:
				# Only 2 or less types, use more space for label
				split = row.split(factor=0.55)

			c = split.column(align=True)
			for s,bset in enumerate(settings.sets):
				r = c.row(align=True)
				r.active = not (tt_settings().bake_force == "Single" and s > 0)

				if bset.has_issues:
					r.operator("uv.ttbake_select_bake_set", text=bset.name, icon='ERROR').select_set = bset.name 
				else:
					r.operator("uv.ttbake_select_bake_set", text=bset.name).select_set = bset.name 


			c = split.column(align=True)
			for bset in settings.sets:
				r = c.row(align=True)
				r.alignment = "LEFT"

				if len(bset.objects_low) > 0:
					r.label(text=f'{len(bset.objects_low)}', icon_value=icon_get("bake_obj_low"))
				elif count_types['low'] > 0:
					r.label(text="")

				if len(bset.objects_high) > 0:
					r.label(text=f'{len(bset.objects_high)}', icon_value=icon_get("bake_obj_high"))
				elif count_types['high'] > 0:
					r.label(text="")

				if len(bset.objects_float) > 0:
					r.label(text=f'{len(bset.objects_float)}', icon_value=icon_get("bake_obj_float"))
				elif count_types['float'] > 0:
					r.label(text="")

				if len(bset.objects_cage) > 0:
					r.label(text=f'{len(bset.objects_cage)}', icon_value=icon_get("bake_obj_cage"))
				elif count_types['cage'] > 0:
					r.label(text="")

			# Force single or multi texture baking
			col = box2.column(align=True)
			col.prop(tt_settings(), "bake_force", text="Force")
			if tt_settings().bake_force == "Single" and len(settings.sets) > 0:
				row.label(text=f"'{settings.sets[0].name}'")


		col = box.column(align=True)
		col.operator(op_bake_organize_names.op.bl_idname, text=f'Organize {len(bpy.context.selected_objects)}x', icon='BOOKMARKS')
		col.operator(op_bake_explode.op.bl_idname, text="Explode", icon_value=icon_get("op_bake_explode"))






class TTBAKE_MT_color_io(Menu):
	bl_idname = "TTBAKE_MT_color_io"
	bl_label = "IO"

	def draw(self, context):
		layout = self.layout

		layout.operator(op_color_io_export.op.bl_idname, text="Export Colors", icon = 'EXPORT')
		layout.operator(op_color_io_import.op.bl_idname, text="Import Colors", icon = 'IMPORT')




class TTBAKE_MT_color_from(Menu):
	bl_idname = "TTBAKE_MT_color_from"
	bl_label = "From"
	bl_description = "Create Color IDs from ..."

	def draw(self, context):
		layout = self.layout
		layout.operator(op_color_from_elements.op.bl_idname, text="Mesh Elements", icon_value = icon_get('op_color_from_elements'))
		layout.operator(op_color_from_materials.op.bl_idname, text="Materials", icon_value = icon_get('op_color_from_materials'))
		layout.operator(op_color_from_directions.op.bl_idname, text="Directions", icon_value = icon_get('op_color_from_directions'))
			



class TTBAKE_MT_color_to(Menu):
	bl_idname = "TTBAKE_MT_color_to"
	bl_label = "To"
	bl_description = "Convert Color IDs into ..."

	def draw(self, context):
		layout = self.layout
		layout.operator(op_color_convert_texture.op.bl_idname, text="Texture Atlas", icon_value = icon_get('op_color_convert_texture'))
		layout.operator(op_color_convert_vertex_colors.op.bl_idname, text="Vertex Colors", icon_value = icon_get("op_color_convert_vertex_colors"))





class TTBAKE_PT_color_id(Panel):
	bl_label = " "
	bl_space_type = 'IMAGE_EDITOR'
	bl_region_type = 'UI'
	bl_category = "TexTools Bake"
	bl_options = {'DEFAULT_CLOSED'}

	def draw_header(self, _):
		layout = self.layout
		row = layout.row(align=True)
		if bpy.context.preferences.addons[__package__].preferences.bool_help:
			row.operator("wm.url_open", text="", icon='INFO').url = "http://renderhjs.net/textools/blender/index.html#colorid"
		row.label(text ="Color ID")

	def draw(self, context):
		layout = self.layout
		# layout.label(text="Select face and color")

		"""
		if bpy.context.scene.render.engine not in ('CYCLES', 'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
			row = layout.row(align=True)
			row.alert = True
			row.operator("uv.textools_enable_cycles", text="Enable 'CYCLES'", icon='CANCEL') #, icon='UV_SYNC_SELECT'
			return
		"""

		box = layout.box()
		col = box.column(align=True)

		def color_mode_icon():
			if tt_settings().color_assign_mode == 'MATERIALS':
				return icon_get("op_color_from_materials")
			else:
				return icon_get("op_color_convert_vertex_colors")

		row = col.row(align=True)
		split = row.split(factor=0.25, align=True)
		c = split.column(align=True)
		c.label(text="Mode:")
		c = split.column(align=True)
		c.prop(tt_settings(), "color_assign_mode", text="", icon_value = color_mode_icon())
		col.separator()

		row = col.row(align=True)
		split = row.split(factor=0.60, align=True)
		c = split.column(align=True)
		c.prop(tt_settings(), "color_ID_templates", text="")
		c = split.column(align=True)
		c.prop(tt_settings(), "color_ID_count", text="", expand=False)

		row = box.row(align=True)
		row.operator(op_color_clear.op.bl_idname, text="Clear", icon = 'X')
		row.menu(TTBAKE_MT_color_io.bl_idname, icon='COLOR')


		max_columns = 5
		if tt_settings().color_ID_count < max_columns:
			max_columns = tt_settings().color_ID_count

		count = math.ceil(tt_settings().color_ID_count / max_columns)*max_columns

		# TODO: Simplify

		for i in range(count):

			if i%max_columns == 0:
				row = box.row(align=True)

			col = row.column(align=True)
			if i < tt_settings().color_ID_count:
				col.prop(tt_settings(), f"color_ID_color_{i}", text='')
				col.operator(op_color_assign.op.bl_idname, text='', icon="FILE_TICK").index = i
	
				if bpy.context.active_object:
					if bpy.context.active_object in bpy.context.selected_objects:
						if len(bpy.context.selected_objects) == 1:
							if bpy.context.active_object.type == 'MESH' and context.scene.ttBakeSettings.color_assign_mode == 'MATERIALS':
								col.operator(op_color_select.op.bl_idname, text="", icon = "FACESEL").index = i
							else:
								col.operator(op_color_select_vertex.op.bl_idname, text="", icon = "FACESEL").index = i
			else:
				col.label(text=" ")

		if context.scene.ttBakeSettings.color_assign_mode != "MATERIALS":
			row = box.row(align=True)
			row.prop(context.scene.ttBakeSettings, "vertex_color_threshold", text="Threshold", expand=True)

		col = box.column(align=True)
		col.label(text="Convert:")
		row = col.row(align=True)
		row.menu(TTBAKE_MT_color_from.bl_idname)  # icon='IMPORT'
		row.menu(TTBAKE_MT_color_to.bl_idname,)	  # icon='EXPORT'





def menu_IMAGE_MT_image(self, context):
	layout = self.layout
	layout.separator()
	layout.operator(op_texture_preview.op.bl_idname, text="Preview Baked Texture", icon_value=icon_get("op_texture_preview"))
	layout.operator(op_texture_preview_cleanup.op.bl_idname, text="Preview Baked Texture cleanup", icon='TRASH')



classes = (
	op_bake.op,
	op_bake_explode.op,
	op_bake_organize_names.op,
	op_texture_preview.op,
	op_texture_preview_cleanup.op,
	op_texture_save.op,
	op_texture_open.op,
	op_texture_select.op,
	op_texture_remove.op,
	op_color_assign.op,
	op_color_clear.op,
	op_color_convert_texture.op,
	op_color_convert_vertex_colors.op,
	op_color_from_elements.op,
	op_color_from_materials.op,
	op_color_from_directions.op,
	op_color_io_export.op,
	op_color_io_import.op,
	op_color_select.op,
	op_color_select_vertex.op,
	utilities_ui.op_popup,
	UV_OT_op_select_bake_set,
	UV_OT_op_select_bake_type,
	TexToolsBakeSettings,
	TTBAKE_PT_bake,
	TTBAKE_MT_color_io,
	TTBAKE_MT_color_from,
	TTBAKE_MT_color_to,
	TTBAKE_PT_color_id,
	Panel_Preferences,
)

icons = (
	"bake_anti_alias",
	"bake_color_space",
	"bake_obj_cage",
	"bake_obj_float",
	"bake_obj_high",
	"bake_obj_low",
	"op_bake",
	"op_bake_explode",
	"op_color_convert_texture",
	"op_color_convert_vertex_colors",
	"op_color_from_directions",
	"op_color_from_elements",
	"op_color_from_materials",
	"op_texture_preview",
	"op_texture_save",
	"op_texture_open",
)


def register():
	for c in classes:
		bpy.utils.register_class(c)

	bpy.types.Scene.ttBakeSettings = PointerProperty(type=TexToolsBakeSettings)

	utilities_ui.register()
	for icon in icons:
		utilities_ui.icon_register(icon)

	bpy.types.IMAGE_MT_image.append(menu_IMAGE_MT_image)


def unregister():
	bpy.types.IMAGE_MT_image.remove(menu_IMAGE_MT_image)
	utilities_ui.unregister()

	for c in reversed(classes):
		try:
			bpy.utils.unregister_class(c)
		except RuntimeError as e:
			print(e)

	# Scene.ttBakeSettings is kept on purpose so the settings saved in .blend files are not lost


if __name__ == "__main__":
	register()
