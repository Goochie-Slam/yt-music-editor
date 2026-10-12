# Visual Effects for Static-Image Music Playlist Videos

## Purpose
A reusable reference for an AI video editor or prompt-writing agent. Use these effects to turn a still image into a subtle, polished visual background for music playlist videos.

## General Rules
- Preserve the original subject, composition, typography, and key details.
- Keep motion subtle and smooth; the music and image remain the focus.
- Prefer seamless loops for long-form videos.
- Avoid excessive flicker, rapid cuts, aggressive glitching, strong camera shake, or distracting movement unless explicitly requested.
- Do not combine every effect at once. Usually select 2–3 compatible effects.
- Match effect intensity and color to the music genre and visual mood.
- If an effect needs motion footage (rain, smoke, dust, light leaks), use a clean overlay and blend it naturally into the image.
- For audio-reactive effects, use the actual audio signal. Do not imply a visualizer is audio-reactive if it is only animated decor.
- Avoid warping faces, changing product artwork, distorting text, or inventing new objects.

## Effect Library

### 1. Film Grain
**Purpose:** Add analog texture and cinematic character.
**Method:** Overlay fine, organic 35mm-style grain across the image.
**Starting intensity:** Low to moderate; roughly 10–25% overlay opacity when using a typical grain layer.
**Best for:** Alternative R&B, Bossa Nova, Jazz, vintage Christmas, retro playlists.
**Avoid:** Coarse noise that reduces readability or makes the image look low quality.

### 2. Light Leak / Bokeh
**Purpose:** Add soft, atmospheric light movement.
**Method:** Use warm light leaks, blurred light orbs, or bokeh drifting slowly across the frame; Screen/Add blending can help.
**Starting intensity:** About 10–30% opacity, adjusted to the source.
**Best for:** R&B, love songs, Christmas, sunset jazz, romantic playlists.
**Avoid:** Bright flares over faces, titles, or important visual details.

### 3. Fog / Smoke
**Purpose:** Create depth and a dreamy or mysterious atmosphere.
**Method:** Place a thin, semi-transparent smoke or haze layer that drifts slowly.
**Best for:** Alternative R&B, dark jazz, lofi, chill music.
**Implementation note:** A black-background smoke overlay can often be blended with Screen mode.
**Avoid:** Dense smoke that obscures the subject or looks like a major scene change.

### 4. Rain Overlay
**Purpose:** Convey a rainy-night, reflective, or melancholic mood.
**Method:** Add gentle falling rain, rain on glass, or subtle water streaks.
**Best for:** Sad R&B, lofi, sleep music, piano playlists.
**Scene matching:** Rain-on-window overlays suit indoor scenes; visible falling rain suits outdoor streets.
**Avoid:** Rain direction, scale, or reflections that conflict strongly with the original scene.

### 5. Slow Zoom / Ken Burns
**Purpose:** Make a still image feel gently alive.
**Method:** Slowly zoom in or out, optionally combined with a very small horizontal or vertical pan.
**Starting motion:** For example, 100% to 105–110% over 30–60 seconds.
**Best for:** Almost every playlist genre.
**Loop note:** For a seamless loop, use a slow return, alternate forward/reverse movement, or hide the reset with a suitable transition.
**Avoid:** Fast zooms, excessive reframing, or cropping out important text and subjects.

### 6. VHS / Chromatic Aberration
**Purpose:** Create a retro tape or analog-video aesthetic.
**Method:** Apply subtle scanlines, slight RGB separation, tape noise, or occasional restrained signal distortion.
**Best for:** 80s/90s music, retro R&B, synthwave, disco.
**Avoid:** Constant heavy glitching, unreadable text, and strong distortion in calm playlists.

### 7. Floating Dust / Particles
**Purpose:** Add delicate movement and atmospheric depth.
**Method:** Use small particles drifting slowly through a light beam or across the scene.
**Best for:** Bossa Nova, jazz café, classical, lofi, cozy indoor scenes.
**Starting intensity:** Low density, small particle size, slow speed.
**Avoid:** Large, bright particles that resemble snow unless snow is intended.

### 8. Audio Spectrum / Waveform
**Purpose:** Visually connect the video to the music.
**Method:** Add a restrained circular spectrum, frequency bars, or waveform.
**Best for:** EDM, Pinoy disco, remixes, hip-hop, R&B.
**Placement:** Keep it small and away from the title and main subject.
**Requirement:** If described as audio-reactive, animate it from the actual audio amplitude/frequency data.
**Avoid:** Oversized visualizers that dominate the artwork.

### 9. Glow / Bloom
**Purpose:** Make bright sources feel soft, luminous, and atmospheric.
**Method:** Add controlled bloom around practical lights, candles, neon, fairy lights, or Christmas lights.
**Best for:** Christmas playlists, romantic music, city pop, jazz lounge, sunset scenes.
**Avoid:** Blowing out highlights, washing out the image, or applying excessive glow to the entire frame.

### 10. Parallax / 2.5D
**Purpose:** Create a sense of depth from a still image.
**Method:** Separate foreground, subject, and background into layers; move them at slightly different speeds to simulate a gentle camera move.
**Best for:** Character-based R&B art, Paris Christmas scenes, city streets, Bossa Nova imagery.
**Requirements:** Clear depth separation and believable reconstruction behind separated objects.
**Avoid:** Warped faces, stretched objects, exposed cutout edges, or excessive perspective changes.

## Additional Seasonal Effect: Snowfall
**Purpose:** Add a recognizable Christmas or winter atmosphere.
**Method:** Overlay soft snowflakes at varied sizes and depths, moving at a calm, consistent speed.
**Best for:** Christmas playlists, winter jazz, holiday music.
**Avoid:** Dense snow that obscures text or looks like a blizzard unless requested.

## Genre Presets

### Preset A — Late-Night / Alternative R&B
- Slow Zoom
- Film Grain
- Very subtle Light Leak or Bokeh
- Mood: intimate, cinematic, moody, restrained
- Motion: slow and nearly unnoticeable

### Preset B — Bossa Nova / Brazilian Jazz Café
- Slow Zoom
- Floating Dust
- Soft Glow
- Mood: warm, elegant, relaxed, sunlit or golden-hour
- Motion: gentle and organic

### Preset C — Pinoy Disco / Party Remix
- Audio Spectrum
- Controlled Glow
- Subtle moving lights or restrained VHS texture
- Mood: energetic, colorful, retro
- Motion: rhythmic but not visually overwhelming

### Preset D — Christmas Playlist
- Glow / Bloom
- Bokeh
- Snowfall
- Optional Slow Zoom
- Mood: cozy, festive, magical
- Motion: gentle, seamless, warm

### Preset E — Lofi / Sad Music
- Rain Overlay
- Film Grain
- Slow Zoom
- Mood: introspective, rainy, quiet
- Motion: soft and continuous

### Preset F — Synthwave / Retro
- VHS texture
- Chromatic Aberration
- Audio Spectrum
- Mood: neon, nostalgic, electronic
- Motion: restrained glitching with controlled rhythm

## AI Instruction Template

When given a still image, a music genre, and a desired mood:

1. Preserve the image's original composition and all important subjects, faces, logos, and text.
2. Select only 2–3 effects from the Effect Library that suit the genre and mood.
3. Specify which elements move, their direction, speed, intensity, and loop behavior.
4. Keep the camera movement subtle unless a stronger move is explicitly requested.
5. Make the result suitable for a long-form music playlist: no distracting cuts, no abrupt resets, and no unnecessary new objects.
6. If the output is a video-generation prompt, describe the movement as continuous and seamless, and explicitly state what must remain still.
7. If the output is an editing recipe, name the effect, layer/blend approach when relevant, and suggested starting intensity.
8. Never claim that an effect is synchronized to the music unless actual audio-reactive data is available.

### Prompt Skeleton
"Animate this still image into a subtle, seamless music-playlist background. Preserve the original composition, subject identity, colors, and all text. Apply [EFFECT 1] at [INTENSITY] and [EFFECT 2] with [DIRECTION / SPEED]. Add [CAMERA MOTION] only if appropriate. Keep the movement slow, polished, and loop-friendly. Do not introduce new objects, distort faces, warp text, or obscure important details. Match the visual mood to [GENRE / MOOD]."

## Quick Selection Guide

| Goal | Recommended effects |
|---|---|
| Cinematic / analog | Film Grain + Slow Zoom |
| Romantic / glowing | Bokeh + Glow + Slow Zoom |
| Rainy / melancholic | Rain + Film Grain + Slow Zoom |
| Cozy café / vintage | Floating Dust + Glow + Slow Zoom |
| Energetic / music-driven | Audio Spectrum + Glow |
| Retro / VHS | VHS + Chromatic Aberration |
| Dreamy / mysterious | Fog + Light Leak |
| Christmas / winter | Snowfall + Bokeh + Glow |
| Depth from a still image | Parallax + Slow Zoom |

## Final Quality Checklist
- [ ] Main subject, face, artwork, and text remain unchanged and readable.
- [ ] Motion is subtle and consistent with the genre.
- [ ] No visible loop jump or abrupt reset.
- [ ] Effects do not compete with the music or title.
- [ ] Brightness, grain, and contrast remain controlled.
- [ ] Only a small number of compatible effects are used.
- [ ] The result still reads as the same original image.
