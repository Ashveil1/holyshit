# Black Hole (Interstellar-style) — Design Spec

Date: 2026-10-02
Status: approved in chat, awaiting spec review

## Goal
Single self-contained HTML file rendering a beautiful real-time black hole
visualization inspired by Interstellar's Gargantua: gravitational lensing,
photon ring, thin glowing accretion disk with Doppler beaming.

## Deliverable
- `blackhole_interstellar.html` in repo root.
- No build step, no external assets, no dependencies beyond a browser with WebGL.

## Rendering approach
- WebGL fullscreen quad, one fragment shader.
- Ray marching: step rays from camera, bend direction by approximate Kerr-ish
  gravity (Schwarzschild-style falloff, spin parameter shifts frame drag feel).
- Background: procedural star field + faint milky-way band, sampled with bent
  ray direction (lensing).
- Black hole shadow: rays captured within capture radius go black.
- Photon ring: thin bright annulus at capture boundary.
- Accretion disk: thin annulus in equatorial plane; visibility where ray
  crosses the plane within disk radii; brightness modulated by
  Doppler beaming (approaching side brighter) and temperature color ramp
  (white-hot inner, orange outer).
- Disk crossing both above and below the shadow via the bent ray path, giving
  the Interstellar "halo" arc look.
- Bloom/glow: cheap additive highlight on bright pixels.

## Interaction
- Mouse drag: orbit camera.
- Wheel: zoom (camera distance).
- Sliders: spin (0..0.99), disk brightness, disk width, disk tilt, bloom,
  render scale.

## Performance
- Internal render scale slider (e.g. 0.5–1.0) upscaled to canvas.
- RequestAnimationFrame loop; pause when tab hidden.

## Non-goals
- Full numerical geodesic integrator in Kerr metric (approach B).
- Loading external textures/models.
