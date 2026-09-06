import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FORM4TH AI Agent",
  description: "AI infrastructure health dashboard for FORM4TH.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
