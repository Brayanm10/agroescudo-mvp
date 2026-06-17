import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgroEscudo",
  description: "Dashboard operativo para riesgo postcosecha",
  icons: {
    icon: "/brand/logo-vertical-campo.png",
    apple: "/brand/logo-vertical-campo.png"
  }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
