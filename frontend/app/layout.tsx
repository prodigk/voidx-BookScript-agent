import type {Metadata} from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bookscript Studio",
  description: "로컬 도서 노트에서 근거 기반 영상 대본을 설계합니다.",
};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
