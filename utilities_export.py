import os

import bpy
import numpy as np

from .settings import tt_settings, prefs


FORMATS = {
	'PNG': ('PNG', '.png'),
	'TARGA': ('TARGA', '.tga'),
	'TIFF': ('TIFF', '.tif'),
	'OPEN_EXR': ('OPEN_EXR', '.exr'),
}

SRGB_SPACES = {'sRGB', 'Utility - sRGB - Texture'}

# ORM channel order and the value used when a map has not been baked yet
ORM_CHANNELS = (
	('ao', 1.0),
	('roughness', 0.5),
	('metallic', 0.0),
)


def wants_float():
	"""Float buffers for 32 bit bakes, and always when auto saving to EXR (8 bit images can't be written to EXR losslessly)."""
	if prefs().bake_32bit_float == '32':
		return True
	settings = tt_settings()
	return settings.bake_auto_save and settings.bake_file_format == 'OPEN_EXR'


def get_output_dir():
	"""Absolute output folder, or None when a relative path can't be resolved (unsaved .blend)."""
	folder = tt_settings().bake_save_dir.strip() or "//textures"
	if folder.startswith("//") and not bpy.data.filepath:
		return None
	return bpy.path.abspath(folder)


def save_image(image):
	"""Save a baked image to the output folder. Returns the saved path or None."""
	folder = get_output_dir()
	if folder is None:
		return None
	os.makedirs(folder, exist_ok=True)

	file_format, ext = FORMATS.get(tt_settings().bake_file_format, FORMATS['PNG'])
	name = bpy.path.clean_name(image.name)
	if image.source == 'TILED':
		filename = f"{name}.<UDIM>{ext}"
	else:
		filename = f"{name}{ext}"
	filepath = os.path.join(folder, filename)

	image.file_format = file_format
	image.filepath_raw = filepath
	image.save()
	image.filepath = filepath
	return filepath


def _srgb_to_linear(values):
	return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def _channel(image, size):
	"""Linear grayscale values (red channel) of an image, resized to size, as a flat float32 array."""
	if tuple(image.size) != tuple(size):
		image = image.copy()
		image.scale(*size)
		temp = image
	else:
		temp = None
	pixels = np.empty(size[0] * size[1] * 4, dtype=np.float32)
	image.pixels.foreach_get(pixels)
	red = pixels[0::4]
	# Byte buffers return the stored (encoded) values, float buffers are already scene linear
	if not image.is_float and image.colorspace_settings.name in SRGB_SPACES:
		red = _srgb_to_linear(red)
	if temp:
		bpy.data.images.remove(temp)
	return red


def find_baked(set_name, mode):
	return bpy.data.images.get(f"{set_name}_{mode}")


def pack_orm(set_name, size):
	"""Pack <set>_ao, <set>_roughness and <set>_metallic into <set>_ORM. Returns (image, missing modes)."""
	sources = [(mode, default, find_baked(set_name, mode)) for mode, default in ORM_CHANNELS]
	found = [img for _, _, img in sources if img]
	if not found:
		return None, [mode for mode, _ in ORM_CHANNELS]

	width = max(img.size[0] for img in found) or size[0]
	height = max(img.size[1] for img in found) or size[1]
	count = width * height

	out = np.ones(count * 4, dtype=np.float32)
	missing = []
	for index, (mode, default, img) in enumerate(sources):
		if img:
			out[index::4] = _channel(img, (width, height))
		else:
			out[index::4] = default
			missing.append(mode)

	name = f"{set_name}_ORM"
	image = bpy.data.images.get(name)
	if image and (tuple(image.size) != (width, height) or image.source != 'GENERATED'):
		bpy.data.images.remove(image)
		image = None
	if image is None:
		image = bpy.data.images.new(name, width=width, height=height, alpha=True,
									float_buffer=wants_float())
	image.colorspace_settings.name = 'Non-Color'
	image.pixels.foreach_set(np.clip(out, 0.0, 1.0))
	image.update()
	return image, missing
