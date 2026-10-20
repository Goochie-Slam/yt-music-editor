/* Generated from shared/schema/project.schema.json by: npm run gen:types. Do not edit. */

export type Curve = "equal-power" | "linear" | "log" | "s-curve";
export type Curve1 = "equal-power" | "linear" | "log" | "s-curve";
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Curve".
 */
export type Curve2 = "equal-power" | "linear" | "log" | "s-curve";

export interface Project {
  schemaVersion: 1;
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  library: LibraryItem[];
  libraryExport: LibraryExport;
  mix: Mix;
  video: Video;
  export: ExportSettings;
}
/**
 * A segment has no cache_wav of its own: it plays a range of its parent's WAV (F1.5).
 *
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "LibraryItem".
 */
export interface LibraryItem {
  id: string;
  title: string;
  source: FileSource | UrlSource | SegmentSource;
  cacheWav: string | null;
  duration: number | null;
  srcBitrateKbps: number | null;
  srcFormat: string;
  srcLossless: boolean;
  error: string | null;
  loudness: Loudness | null;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "FileSource".
 */
export interface FileSource {
  kind: "file";
  path: string;
  uploaded: boolean;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "UrlSource".
 */
export interface UrlSource {
  kind: "url";
  url: string;
  site: string;
  remoteId: string;
}
/**
 * A piece cut from another library item by the tracklist splitter (F1.5).
 *
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "SegmentSource".
 */
export interface SegmentSource {
  kind: "segment";
  parentId: string;
  start: number;
  end: number;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Loudness".
 */
export interface Loudness {
  integrated: number;
  truePeak: number;
  lra: number;
}
/**
 * Settings of the batch MP3 export (F1.4); remembered per project.
 *
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "LibraryExport".
 */
export interface LibraryExport {
  folder: string;
  pattern: string;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Mix".
 */
export interface Mix {
  targetLufs: -16 | -14 | -12;
  autoTrimSilence: boolean;
  fadeInStart: number;
  fadeOutEnd: number;
  tracks: MixTrack[];
  transitions: {
    [k: string]: Transition;
  };
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "MixTrack".
 */
export interface MixTrack {
  id: string;
  libId: string;
  title: string;
  trimIn: number;
  trimOut: number | null;
  gainDb: number;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Transition".
 */
export interface Transition {
  presetId: string | null;
  fadeOut: number;
  fadeIn: number;
  overlap: number;
  curveOut: Curve;
  curveIn: Curve1;
  edited: boolean;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Video".
 */
export interface Video {
  format: "16:9" | "9:16";
  background: Background;
  artwork: Artwork;
  effects: Effects;
  elements: (TextElement | NowPlayingElement | ImageElement | OverlayElement | VisualizerElement)[];
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Background".
 */
export interface Background {
  fit: "blur" | "solid" | "crop";
  blur: number;
  dim: number;
  solid: string;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Artwork".
 */
export interface Artwork {
  type: "image" | "carousel" | "video";
  media: string[];
  carouselMode: "song" | "interval";
  carouselEverySec: number;
  loopCrossfade: boolean;
  scale: number;
  radius: number;
  shadow: boolean;
  border: boolean;
  pos: PosByFormat;
}
/**
 * Element positions are stored separately per aspect ratio (F3.49).
 *
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "PosByFormat".
 */
export interface PosByFormat {
  "16:9": Pos;
  "9:16": Pos;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Pos".
 */
export interface Pos {
  x: number;
  y: number;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "Effects".
 */
export interface Effects {
  zoom: EffectSetting;
  grain: EffectSetting;
  glow: EffectSetting;
  dust: EffectSetting;
  snow: EffectSetting;
  bokeh: EffectSetting;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "EffectSetting".
 */
export interface EffectSetting {
  on: boolean;
  value: number;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "TextElement".
 */
export interface TextElement {
  start: number;
  end: number | null;
  id: string;
  name: string;
  visible: boolean;
  kind: "text";
  text: string;
  font: "Be Vietnam Pro" | "Inter" | "Playfair Display" | "Montserrat" | "Lora" | "Quicksand";
  weight: 400 | 500 | 600 | 700 | 800;
  size: number;
  color: string;
  shadow: boolean;
  anim: "fade" | "none";
  pos: PosByFormat;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "NowPlayingElement".
 */
export interface NowPlayingElement {
  id: string;
  name: string;
  visible: boolean;
  kind: "nowPlaying";
  fmt: "{title}" | "{index}. {title}" | "Now Playing — {title}";
  label: boolean;
  font: "Be Vietnam Pro" | "Inter" | "Playfair Display" | "Montserrat" | "Lora" | "Quicksand";
  size: number;
  color: string;
  anim: "fade" | "slide" | "none";
  pos: PosByFormat;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "ImageElement".
 */
export interface ImageElement {
  start: number;
  end: number | null;
  id: string;
  name: string;
  visible: boolean;
  kind: "image";
  file: string;
  size: number;
  opacity: number;
  pos: PosByFormat;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "OverlayElement".
 */
export interface OverlayElement {
  start: number;
  end: number | null;
  id: string;
  name: string;
  visible: boolean;
  kind: "overlay";
  sub: "video" | "image" | "color";
  file: string | null;
  mode: "solid" | "gradient" | "vignette";
  direction: "bottom" | "top" | "left" | "right";
  color: string;
  blend: "normal" | "screen" | "add" | "overlay" | "multiply" | "softlight";
  opacity: number;
  loopCrossfade: boolean;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "VisualizerElement".
 */
export interface VisualizerElement {
  id: string;
  name: string;
  visible: boolean;
  kind: "visualizer";
  type: "bars" | "wave" | "circular";
  style: 0 | 1 | 2;
  color1: string;
  color2: string;
  size: number;
  sensitivity: number;
  opacity: number;
  pos: PosByFormat;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "ExportSettings".
 */
export interface ExportSettings {
  formats: ("16:9" | "9:16")[];
  height: 1080 | 1440 | 2160;
  fps: 30 | 60;
  quality: "light" | "balanced" | "high";
  encoder: "auto" | "nvenc" | "x264";
  extras: ExportExtras;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "ExportExtras".
 */
export interface ExportExtras {
  mixMp3: boolean;
  chapters: boolean;
}
/**
 * This interface was referenced by `Project`'s JSON-Schema
 * via the `definition` "ProjectSummary".
 */
export interface ProjectSummary {
  id: string;
  name: string;
  path: string;
  updatedAt: string;
}
