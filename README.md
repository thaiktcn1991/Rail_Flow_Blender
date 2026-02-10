# Rail Flow Blender

Advanced retopology tool for Blender, ported from Rail Flow Maya.

## Features

- **Poly Draw Mode**: Draw quad patches on mesh surface
- **Tube Mode**: Create cylindrical meshes along strokes
- **Smart Snapping**: Automatic vertex snapping to source surface
- **Real-time Preview**: See your strokes before generating mesh

## Installation

1. Download the latest release
2. In Blender: Edit > Preferences > Add-ons > Install
3. Select the downloaded .zip file
4. Enable "Rail Flow" in the add-ons list

## Usage

1. Select your high-poly source mesh
2. Open the Rail Flow panel in the 3D View sidebar (N key)
3. Click a drawing mode (Poly Draw or Tube)
4. Draw strokes on the surface with LMB
5. Press ENTER to generate mesh, ESC to cancel

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| LMB | Draw stroke |
| ENTER | Confirm and generate mesh |
| ESC | Cancel |
| RMB | Clear current stroke |

## Development Status

This is a work in progress. Currently implemented:

- [x] Core geometry utilities (RMF algorithm)
- [x] Spatial acceleration (BVH Tree)
- [x] Poly Draw mode (basic)
- [x] Tube mode (basic)
- [x] UI Panel
- [ ] Bridge mode
- [ ] Fill Hole mode
- [ ] Edge Loop mode
- [ ] Mirror support
- [ ] Advanced snapping

## Credits

- Original Maya version by ThaiLuong
- Blender port by ThaiLuong (thaiktcn1991)

## License

GPL-3.0 (required for Blender add-ons)
