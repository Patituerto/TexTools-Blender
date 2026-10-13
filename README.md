# TexTools Bake

Community fork of [TexTools](https://github.com/franMarz/TexTools-Blender) that keeps only the **Baking** and **Color ID** tools, updated for **Blender 5.0+**.

TexTools was created by [renderhjs](https://github.com/renderhjs), ported to Blender 2.80 by [Sav Martin](https://github.com/SavMartin) and maintained by [franMarz](https://github.com/franMarz). All credit for the original tools goes to them.

## Features
- 40+ bake modes (normals, AO, curvature, cavity, PBR channels, IDs, thickness…), single or high-to-low with automatic pairing by name (`_low`, `_high`, `_cage`, `_float`).
- **Bake ORM**: one click bakes AO, Roughness and Metallic and packs them into a single `<set>_ORM` texture (R = AO, G = Roughness, B = Metallic, linear) for Unreal, Unity and Godot. The refresh button re-packs already baked maps.
- **Auto Save**: writes every baked texture to a folder (default `//textures/`, next to the .blend) as PNG, TGA, TIFF or EXR.
- Color ID: assign ID colors as materials or vertex colors, convert to texture atlas.
- Can be installed side by side with the original TexTools (separate tab and operator IDs).

## Install
Blender 4.2+: *Edit > Preferences > Get Extensions > Install from Disk* and pick the `.zip`.
The panel lives in the **Image Editor > Sidebar (N) > TexTools Bake** tab.

## License
GNU GPL v3 or later, same as the original TexTools. See `LICENSE.txt`.
