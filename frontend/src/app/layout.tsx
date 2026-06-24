import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Echoes",
  description:
    "Aventuras interactivas generadas por IA, personalizadas e infinitas.",
};

// Aplica las preferencias de lectura persistidas ANTES del primer paint para
// evitar un flash con los valores por defecto. Espeja el enfoque de next-themes.
// Los mapas se duplican aquí a propósito: este script corre antes de cargar el
// bundle (no puede importar de settings-store).
const PREFERENCIAS_PRE_PAINT = `(function(){try{var raw=localStorage.getItem('aventuras-settings');if(!raw)return;var s=(JSON.parse(raw)||{}).state||{};var fonts={serif:'"Crimson Text", Georgia, serif',sans:'"Atkinson Hyperlegible", Inter, system-ui, sans-serif',dyslexic:'"Lexend Deca", "Comic Sans MS", sans-serif'};var sizes={sm:'0.95rem',md:'1.05rem',lg:'1.2rem'};var r=document.documentElement;if(fonts[s.narrativaFont])r.style.setProperty('--font-narrativa',fonts[s.narrativaFont]);if(sizes[s.narrativaSize])r.style.setProperty('--narrativa-size',sizes[s.narrativaSize]);}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: PREFERENCIAS_PRE_PAINT }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
