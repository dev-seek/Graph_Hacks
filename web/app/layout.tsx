import type { Metadata } from "next";
import { Atkinson_Hyperlegible, Fraunces } from "next/font/google";
import "./globals.css";
import { Footer, Header, TourRoot } from "@/components/Shell";

const atkinson = Atkinson_Hyperlegible({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-atkinson",
  display: "swap",
});

const fraunces = Fraunces({
  weight: ["600", "700"],
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Constellation",
  description:
    "Helps families gather the right evidence and reach the right specialist sooner. It does not diagnose.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${atkinson.variable} ${fraunces.variable}`}>
      <body>
        <a href="#main" className="skip-link">
          Skip to the main content
        </a>
        <Header />
        <TourRoot />
        <main id="main" className="mx-auto max-w-4xl px-4 py-8">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
