import bpy

from . import settings
from . import utilities_bake
from . import utilities_export
from .settings import tt_settings


ORM_MODES = ('ao', 'roughness', 'metallic')


def _set_names():
	if not settings.sets:
		settings.sets = utilities_bake.get_bake_sets()
	if tt_settings().bake_force == "Single" and settings.sets:
		return [settings.sets[0].name]
	return [bset.name for bset in settings.sets]


def _pack_all(operator):
	packed = []
	for set_name in _set_names():
		image, missing = utilities_export.pack_orm(set_name, tt_settings().size)
		if image is None:
			operator.report({'WARNING'}, f"'{set_name}': bake AO, Roughness or Metallic first")
			continue
		if missing:
			operator.report({'INFO'}, f"'{set_name}_ORM': {', '.join(missing)} not baked, default value used")
		if tt_settings().bake_auto_save:
			if not utilities_export.save_image(image):
				operator.report({'WARNING'}, "Auto save skipped: save the .blend file first or choose an absolute folder")
		packed.append(image.name)
	return packed


class op_pack(bpy.types.Operator):
	bl_idname = "uv.ttbake_pack_orm"
	bl_label = "Pack ORM"
	bl_description = "Pack the baked AO (R), Roughness (G) and Metallic (B) maps of each bake set into one <set>_ORM texture"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return len(settings.sets) > 0

	def execute(self, context):
		packed = _pack_all(self)
		if not packed:
			return {'CANCELLED'}
		self.report({'INFO'}, f"Packed {', '.join(packed)}")
		return {'FINISHED'}


class op_bake_orm(bpy.types.Operator):
	bl_idname = "uv.ttbake_bake_orm"
	bl_label = "Bake ORM"
	bl_description = "Bake AO, Roughness and Metallic for the selected bake sets and pack them into <set>_ORM (Unreal, Unity, Godot)"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return len(settings.sets) > 0

	def execute(self, context):
		scene = context.scene
		previous_mode = scene.TTB_bake_mode
		try:
			for mode in ORM_MODES:
				scene.TTB_bake_mode = mode
				if not bpy.ops.uv.ttbake_bake.poll():
					self.report({'ERROR'}, f"Can't bake '{mode}': {settings.bake_error or 'check the selection'}")
					return {'CANCELLED'}
				bpy.ops.uv.ttbake_bake()
		finally:
			scene.TTB_bake_mode = previous_mode

		packed = _pack_all(self)
		if not packed:
			return {'CANCELLED'}
		self.report({'INFO'}, f"Baked and packed {', '.join(packed)}")
		return {'FINISHED'}
