# Frontend — Generador de Aventuras de Texto con IA

Next.js 15 + TypeScript + Tailwind + shadcn/ui. Consume el backend FastAPI.

## Quickstart

```bash
npm install
cp .env.local.example .env.local   # apuntar al backend
npm run dev
```

Abrir http://localhost:3000.

## Estructura

```
src/
├── app/                  # App Router de Next.js
│   ├── layout.tsx        # Layout raíz
│   ├── page.tsx          # Pantalla principal (única)
│   ├── globals.css       # Tema (CSS variables)
│   └── providers.tsx     # React Query provider
├── components/
│   ├── ui/               # Componentes base estilo shadcn (Button, Dialog, etc)
│   ├── inicio-dialog.tsx # Modal inicial: elegir género + personaje
│   ├── turno-card.tsx    # Render de un turno (narrativa + imagen + opciones)
│   ├── acciones.tsx      # Botones de opciones + input libre
│   ├── header.tsx        # Barra superior con objetivo, código, inventario
│   └── final-banner.tsx  # Cierre de aventura
├── lib/
│   ├── api.ts            # Cliente HTTP del backend
│   ├── types.ts          # Tipos del dominio (espejo del backend)
│   ├── utils.ts          # cn() helper
│   └── api-types.ts      # (autogenerado) tipos desde openapi.json
└── store/
    └── partida-store.ts  # Estado global (Zustand): partida actual + historial
```

## Diseño

Una sola pantalla tipo chat. El modal de inicio aparece cuando no hay partida cargada o se hace click en "nueva aventura". El código de partida se persiste en localStorage para poder reanudar.

## Generar tipos desde el backend

Con el backend corriendo en :8000:

```bash
npm run gen:types
```

Esto crea `src/lib/api-types.ts` con todos los schemas del OpenAPI.
