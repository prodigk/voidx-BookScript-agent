import "./index.css";
import {CalculateMetadataFunction, Composition, staticFile} from "remotion";
import {BookVideo} from "./BookVideo";
import manifestJson from "./data/current-video.json";
import {getAudioDuration} from "./get-audio-duration";
import {fitManifestToDuration} from "./timeline";
import type {VideoManifest} from "./types";

const manifest = manifestJson as VideoManifest;
type Props = {manifest: VideoManifest};

const calculateMetadata: CalculateMetadataFunction<Props> = async ({props}) => {
  if (!props.manifest.audio) {
    return {defaultOutName: `${props.manifest.run_id}.mp4`};
  }
  const duration = await getAudioDuration(staticFile(props.manifest.audio.src));
  const durationInFrames = Math.ceil(duration * props.manifest.fps);
  return {
    durationInFrames,
    props: {manifest: fitManifestToDuration(props.manifest, durationInFrames)},
    defaultOutName: `${props.manifest.run_id}.mp4`,
  };
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="BookVideo"
      component={BookVideo}
      durationInFrames={manifest.duration_frames}
      fps={manifest.fps}
      width={manifest.width}
      height={manifest.height}
      defaultProps={{manifest}}
      calculateMetadata={calculateMetadata}
    />
  );
};
