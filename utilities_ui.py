import bpy
import os

from . import utilities_bake
from . import op_bake
import bpy.utils.previews
from .settings import tt_settings, prefs

from bpy.props import StringProperty

class op_popup(bpy.types.Operator):
	bl_idname = "ui.ttbake_popup"
	bl_label = "Message"

	message: StringProperty()

	def execute(self, context):
		self.report({'INFO'}, self.message)
		print(self.message)
		return {'FINISHED'}

	def invoke(self, context, event):
		wm = context.window_manager
		return wm.invoke_popup(self, width=200)

	def draw(self, context):
		self.layout.label(text=self.message)


size_textures = [
	('32', '32', ''),
	('64', '64', ''),
	('128', '128', ''),
	('256', '256', ''),
	('512', '512', ''),
	('1024', '1024', ''),
	('2048', '2048', ''),
	('4096', '4096', ''),
	('8192', '8192', '')
]

# Preview collections (standard bpy.utils.previews, loaded from the PNG files)
preview_icons = None
thumbnail_previews = None


def icon_register(fileName):
	name = fileName.split('.')[0]  # Don't include file extension
	if name in preview_icons:
		return
	icons_location = os.path.join(os.path.dirname(__file__), "icons")
	preview_icons.load(name, os.path.join(icons_location, name + ".png"), 'IMAGE')


def icon_get(name):
	if preview_icons is None or name not in preview_icons:
		return 0
	return preview_icons[name].icon_id


def generate_bake_mode_previews():
	image_location = os.path.join(os.path.dirname(__file__), "resources", "bake_modes")
	enum_items = []
	for i, mode in enumerate(sorted(op_bake.modes)):
		filepath = os.path.join(image_location, mode + ".png")
		icon_id = 0
		if os.path.exists(filepath):
			thumb = thumbnail_previews.load(mode, filepath, 'IMAGE')
			icon_id = thumb.icon_id
		enum_items.append((mode, mode, "", icon_id, i))
	return enum_items


def GetContextView3D():
	for window in bpy.context.window_manager.windows:
		screen = window.screen
		for area in screen.areas:
			if area.type == 'VIEW_3D': 
				for region in area.regions:
					if region.type == 'WINDOW':
						# Stuff the override context with very common requests by operators.  MORE COULD BE NEEDED!
						override = {'window': window, 'screen': screen, 'area': area, 'region': region, 'scene': bpy.context.scene,
									'edit_object': bpy.context.edit_object, 'active_object': bpy.context.active_object,
									'selected_objects': bpy.context.selected_objects}
						return override					
	return None


def GetContextViewUV():
	for window in bpy.context.window_manager.windows:
		screen = window.screen
		for area in screen.areas:
			if area.ui_type == 'UV':
				for region in area.regions:
					if region.type == 'WINDOW':
						# Stuff the override context with very common requests by operators.  MORE COULD BE NEEDED!
						override = {'window': window, 'screen': screen, 'area': area, 'region': region, 'scene': bpy.context.scene,
									'edit_object': bpy.context.edit_object, 'active_object': bpy.context.active_object,
									'selected_objects': bpy.context.selected_objects}
						return override			
	return None


def get_padding():
	return tt_settings().padding / min(tt_settings().size)


def get_bake_mode():
	return str(bpy.context.scene.TTB_bake_mode).lower()


def set_bake_color_space_int(bake_mode):
	color_space = prefs().bake_color_space_def
	if "normal_" in bake_mode:
		return 3 if color_space in ('ASTANDARD', 'APBR') else 1
	elif color_space == 'STANDARD':
		return 0
	elif color_space == 'ASTANDARD':
		return 2
	elif color_space in ('PBR', 'APBR'):
		if (op_bake.modes[bake_mode].material != "") or (bake_mode == 'transmission' and not prefs().bool_clean_transmission) or \
				bake_mode in {'diffuse', 'base_color', 'sss_color', 'emission', 'environment', 'combined'}:
			return 0 if color_space == 'PBR' else 2
		return 1 if color_space == 'PBR' else 3

	if color_space not in {'PBR', 'APBR', 'STANDARD', 'ASTANDARD'}:
		raise NotImplementedError(f'{color_space=} not implement for set_bake_color_space_int()')
	raise NotImplementedError(f'{bake_mode=} is an invalid keyword argument for set_bake_color_space_int()')


def on_bakemode_set(self, context):
	bake_mode = get_bake_mode()
	if set_bake_color_space_int(bake_mode) == 1:
		tt_settings().bake_color_space = 'Non-Color'
	elif set_bake_color_space_int(bake_mode) == 0:
		tt_settings().bake_color_space = 'sRGB'
	elif set_bake_color_space_int(bake_mode) == 3:
		tt_settings().bake_color_space = 'Utility - Linear - sRGB'
	else:
		tt_settings().bake_color_space = 'Utility - sRGB - Texture'
	utilities_bake.on_select_bake_mode(bake_mode)




_bake_mode_items = []


def register():
	global preview_icons, thumbnail_previews, _bake_mode_items
	preview_icons = bpy.utils.previews.new()
	thumbnail_previews = bpy.utils.previews.new()

	# Keep a module level reference to the enum items so their strings stay alive
	_bake_mode_items = generate_bake_mode_previews()
	bpy.types.Scene.TTB_bake_mode = bpy.props.EnumProperty(
		items=_bake_mode_items,
		update=on_bakemode_set,
		default='normal_tangent'
	)


def unregister():
	global preview_icons, thumbnail_previews
	for collection in (thumbnail_previews, preview_icons):
		if collection is not None:
			bpy.utils.previews.remove(collection)
	preview_icons = None
	thumbnail_previews = None
	if hasattr(bpy.types.Scene, "TTB_bake_mode"):
		del bpy.types.Scene.TTB_bake_mode
