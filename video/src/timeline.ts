import type {VideoManifest} from "./types";

export const fitManifestToDuration = (
  manifest: VideoManifest,
  durationFrames: number,
): VideoManifest => {
  let previousEnd = 0;
  const scenes = manifest.scenes.map((scene, index) => {
    const originalEnd = scene.start_frame + scene.duration_frames;
    const scaledEnd =
      index === manifest.scenes.length - 1
        ? durationFrames
        : Math.round((originalEnd / manifest.duration_frames) * durationFrames);
    const startFrame = previousEnd;
    previousEnd = scaledEnd;
    return {
      ...scene,
      start_frame: startFrame,
      duration_frames: scaledEnd - startFrame,
      start_seconds: startFrame / manifest.fps,
      end_seconds: scaledEnd / manifest.fps,
    };
  });
  return {
    ...manifest,
    duration_seconds: durationFrames / manifest.fps,
    duration_frames: durationFrames,
    scenes,
  };
};
