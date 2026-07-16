export type VideoQuote = {
  text: string;
  source: string;
  display_source: string;
  duration_seconds: number;
};

export type VideoScene = {
  section_id: string;
  title: string;
  start_seconds: number;
  end_seconds: number;
  start_frame: number;
  duration_frames: number;
  narration: string;
  visual_intent: string;
  on_screen_text: string[];
  suggested_assets: string[];
  quote: VideoQuote | null;
};

export type VideoAudio = {
  src: string;
  volume: number;
};

export type VideoManifest = {
  schema_version: string;
  run_id: string;
  title: string;
  renderer: "remotion";
  validation_status: "approved";
  fps: number;
  width: number;
  height: number;
  duration_seconds: number;
  duration_frames: number;
  source_script: string;
  audio: VideoAudio | null;
  reference_books: string[];
  scenes: VideoScene[];
};
