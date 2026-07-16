import React from "react";
import {Audio} from "@remotion/media";
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";
import type {VideoManifest, VideoQuote, VideoScene} from "./types";

const palette = {
  ink: "#F6F3EC",
  muted: "#B8C0CB",
  night: "#0B1220",
  nightSoft: "#152338",
  coral: "#FF6B5F",
  coralSoft: "#F5A59E",
  line: "rgba(246, 243, 236, 0.14)",
};

const fontFamily =
  '"Apple SD Gothic Neo", "Pretendard", "Noto Sans KR", system-ui, sans-serif';

const AmbientBackground: React.FC<{index: number}> = ({index}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        background:
          index % 2 === 0
            ? "linear-gradient(145deg, #0B1220 0%, #142237 58%, #0D1828 100%)"
            : "linear-gradient(145deg, #101827 0%, #1A2637 52%, #0B1422 100%)",
      }}
    >
      <div
        style={{
          position: "absolute",
          width: 760,
          height: 760,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,107,95,0.17), rgba(255,107,95,0))",
          right: -180,
          top: -240,
          opacity: interpolate(frame, [0, durationInFrames], [0.55, 0.9], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          scale: interpolate(frame, [0, durationInFrames], [0.92, 1.12], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.45, 0, 0.55, 1),
          }),
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 980,
          height: 980,
          border: `1px solid ${palette.line}`,
          borderRadius: "50%",
          left: -560,
          bottom: -620,
          rotate: `${index * 7}deg`,
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.18,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
        }}
      />
    </AbsoluteFill>
  );
};

const QuoteCard: React.FC<{quote: VideoQuote}> = ({quote}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const fadeOutStart = Math.max(1, durationInFrames - 18);
  return (
    <AbsoluteFill
      style={{
        zIndex: 5,
        padding: "100px 140px",
        alignItems: "center",
        justifyContent: "center",
        background: "#080D17",
        opacity: interpolate(frame, [0, 20, fadeOutStart, durationInFrames], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.45, 0, 0.55, 1),
        }),
      }}
    >
      <div style={{width: "100%", maxWidth: 1420, display: "flex", flexDirection: "column", gap: 54}}>
        <div style={{width: 72, height: 5, borderRadius: 99, background: palette.coral}} />
        <div
          style={{
            color: palette.ink,
            fontFamily,
            fontSize: 72,
            fontWeight: 600,
            lineHeight: 1.48,
            letterSpacing: -1.8,
            wordBreak: "keep-all",
          }}
        >
          {quote.text}
        </div>
        <div
          style={{
            color: palette.muted,
            fontFamily,
            fontSize: 32,
            lineHeight: 1.45,
            wordBreak: "keep-all",
          }}
        >
          {quote.display_source}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Scene: React.FC<{
  scene: VideoScene;
  index: number;
  totalScenes: number;
}> = ({scene, index, totalScenes}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const exitStart = Math.max(fps, durationInFrames - Math.round(fps * 0.8));
  const quoteFrames = scene.quote ? scene.quote.duration_seconds * fps : 0;
  const quoteCharacterIndex = scene.quote ? scene.narration.indexOf(scene.quote.text) : -1;
  const quoteProgress = quoteCharacterIndex >= 0 ? quoteCharacterIndex / scene.narration.length : 0.2;
  const quoteStart = scene.quote
    ? Math.min(
        Math.max(fps, Math.round(durationInFrames * quoteProgress)),
        Math.max(fps, durationInFrames - quoteFrames - fps),
      )
    : 0;
  return (
    <AbsoluteFill style={{fontFamily, color: palette.ink}}>
      <AmbientBackground index={index} />
      <AbsoluteFill
        style={{
          padding: "100px 120px",
          opacity: interpolate(frame, [0, 24, exitStart, durationInFrames], [0, 1, 1, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <div style={{height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between"}}>
          <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
            <div style={{fontSize: 25, fontWeight: 700, color: palette.coralSoft, letterSpacing: 2.8}}>
              CHAPTER {String(index + 1).padStart(2, "0")}
            </div>
            <div style={{fontSize: 24, color: palette.muted}}>
              {index + 1} / {totalScenes}
            </div>
          </div>

          <div style={{display: "flex", flexDirection: "column", gap: 48, maxWidth: 1500}}>
            <h1
              style={{
                margin: 0,
                maxWidth: 1480,
                fontSize: index === 0 ? 104 : 86,
                fontWeight: 700,
                lineHeight: 1.18,
                letterSpacing: -3.6,
                wordBreak: "keep-all",
                textWrap: "balance",
                opacity: interpolate(frame, [4, 34], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                }),
                translate: interpolate(frame, [4, 34], ["0px 34px", "0px 0px"], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                }),
              }}
            >
              {scene.title}
            </h1>
            <div style={{display: "flex", flexDirection: "column", gap: 20}}>
              {scene.on_screen_text.slice(0, 2).map((text, textIndex) => {
                const start = 32 + textIndex * 22;
                return (
                  <div
                    key={text}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 20,
                      color: textIndex === 0 ? palette.ink : palette.muted,
                      fontSize: 42,
                      fontWeight: textIndex === 0 ? 600 : 450,
                      lineHeight: 1.35,
                      wordBreak: "keep-all",
                      opacity: interpolate(frame, [start, start + 24], [0, 1], {
                        extrapolateLeft: "clamp",
                        extrapolateRight: "clamp",
                        easing: Easing.bezier(0.16, 1, 0.3, 1),
                      }),
                    }}
                  >
                    <span style={{width: 10, height: 10, borderRadius: "50%", background: palette.coral}} />
                    {text}
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{display: "flex", flexDirection: "column", gap: 18}}>
            <div style={{height: 4, borderRadius: 99, background: palette.line, overflow: "hidden"}}>
              <div
                style={{
                  height: "100%",
                  width: `${interpolate(frame, [0, durationInFrames], [0, 100], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  })}%`,
                  background: palette.coral,
                }}
              />
            </div>
          </div>
        </div>
      </AbsoluteFill>
      {scene.quote ? (
        <Sequence from={quoteStart} durationInFrames={quoteFrames} premountFor={fps}>
          <QuoteCard quote={scene.quote} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};

const ReferenceCard: React.FC<{books: string[]}> = ({books}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        zIndex: 6,
        padding: "100px 140px",
        justifyContent: "center",
        background: "#080D17",
        fontFamily,
        opacity: interpolate(frame, [0, 24, durationInFrames - 18, durationInFrames], [0, 1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.45, 0, 0.55, 1),
        }),
      }}
    >
      <div style={{display: "flex", flexDirection: "column", gap: 42, maxWidth: 1480}}>
        <div style={{fontSize: 28, fontWeight: 700, color: palette.coralSoft, letterSpacing: 2.8}}>
          REFERENCE BOOKS
        </div>
        <div style={{fontSize: 44, color: palette.muted, lineHeight: 1.45}}>
          이 영상은 다음 책들의 내용을 바탕으로 구성되었습니다.
        </div>
        <div style={{display: "flex", flexDirection: "column", gap: 18}}>
          {books.map((book, index) => (
            <div
              key={book}
              style={{
                fontSize: 68,
                fontWeight: 650,
                lineHeight: 1.3,
                color: palette.ink,
                opacity: interpolate(frame, [18 + index * 10, 42 + index * 10], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.16, 1, 0.3, 1),
                }),
              }}
            >
              『{book}』
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const BookVideo: React.FC<{manifest: VideoManifest}> = ({manifest}) => {
  return (
    <AbsoluteFill style={{backgroundColor: palette.night}}>
      {manifest.audio ? (
        <Audio src={staticFile(manifest.audio.src)} volume={() => manifest.audio?.volume ?? 1} />
      ) : null}
      {manifest.scenes.map((scene, index) => (
        <Sequence
          key={scene.section_id}
          from={scene.start_frame}
          durationInFrames={scene.duration_frames}
          premountFor={manifest.fps}
        >
          <Scene scene={scene} index={index} totalScenes={manifest.scenes.length} />
          {index === manifest.scenes.length - 1 ? (
            <Sequence
              from={Math.max(0, scene.duration_frames - manifest.fps * 12)}
              durationInFrames={manifest.fps * 12}
              premountFor={manifest.fps}
            >
              <ReferenceCard books={manifest.reference_books} />
            </Sequence>
          ) : null}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
