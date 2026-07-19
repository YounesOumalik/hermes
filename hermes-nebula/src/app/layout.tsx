import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "AgentAI - Agent Platform",
  description: "A collaborative autonomous multi-agent platform for power users.",
  manifest: "/manifest.json",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={outfit.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <meta name="theme-color" content="#0a0c10" />
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
