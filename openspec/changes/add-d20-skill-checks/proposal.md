## Why

Today the narrator is the sole author of every outcome: the player declares an action and the LLM decides what happens. With no uncontrolled risk, nothing feels *earned* — the experience reads like an interactive story rather than a game played at a table. The single highest-leverage change toward a D&D-like session is **dice the narrator does not control**: a real, server-rolled d20 whose result the LLM must honor when it narrates. This is Milestone 1 (the irreducible root) of the layered D&D-feel vision; it deliberately ships dice plus a minimal character sheet together, because rolls without modifiers are flavorless and stats without rolls do nothing.

## What Changes

- **New d20 skill-check resolution.** When a player's action has an uncertain outcome, the narrator declares a check (one D&D ability + a difficulty *band*) instead of authoring the result. The backend rolls a real d20 server-side, adds the relevant ability modifier, compares it against the band's fixed DC, and resolves to a critical success / success / failure / critical failure. A natural 20 is always a critical success and a natural 1 always a critical failure, independent of the modifier.
- **Fixed difficulty bands.** The narrator chooses a band (`trivial` 5, `facil` 10, `media` 15, `dificil` 20, `heroica` 25), never a raw DC. The system owns the number so difficulty stays legible and the model cannot silently move the goalposts.
- **Two-phase turn for risky actions.** A turn that requires a check becomes two LLM calls: phase 1 declares the check (ability + band + the in-fiction framing of what's at stake); the backend rolls; phase 2 narrates the outcome consistent with the roll result. Actions the narrator judges trivial or impossible still resolve in a single call with no roll, exactly as today.
- **Minimal character sheet (6 classic D&D attributes).** Character creation also generates the six abilities — Fuerza, Destreza, Constitución, Inteligencia, Sabiduría, Carisma — as 3–18 scores derived from the player's description and genre. Each yields a standard modifier (`floor((score − 10) / 2)`) that feeds checks. The sheet is persisted on the partida and surfaced in the UI.
- **Roll transparency in the UI.** The player sees the declared check, the band/DC, the rolled d20, the applied modifier, and the result tier — the roll *moment* is part of the product, not hidden theater.
- **3D animated dice roll.** The roll is presented as a scripted-rotation 3D d20 (Three.js + react-three-fiber, no physics) that settles on the server-rolled face, with a staged reveal and crit treatments, played as a full-screen overlay that masks the phase-2 latency. The animation is pure presentation over the authoritative server result and degrades to a static reduced-motion fallback.
- The system stays deliberately **D&D-flavored over any other TTRPG**: d20 + ability modifier vs DC with nat-20/nat-1 crits, not a 2d6 partial-success ladder.

This change is scoped to Milestone 1. Persistent leveling heroes, HP/conditions, loot weight, and AI companions are explicitly **out of scope** here and depend on this root.

## Capabilities

### New Capabilities
- `skill-checks`: The d20 resolution mechanic — when the narrator declares a check, the system rolls a real d20 server-side against a fixed difficulty band plus the relevant ability modifier, classifies the result (crit success / success / failure / crit fail with nat-20/nat-1 rules), and drives the two-phase turn that has the narrator honor the rolled outcome.
- `character-sheet`: The six-attribute stat block (Fuerza, Destreza, Constitución, Inteligencia, Sabiduría, Carisma) generated at creation, its derived modifiers, persistence on the partida, backward-compatible defaults for legacy partidas, and its presentation in the UI.

### Modified Capabilities
- `narrative-creation`: The creation contract additionally produces the six ability scores for the new character, derived from the player's description and genre.

## Impact

- **Backend domain** (`app/models/domain.py`): new `Atributos` model on `Personaje`; new persisted check fields on `TurnoHistorial` (declared ability, band, d20, modifier, total, DC, result tier). Legacy partidas deserialize with safe defaults.
- **LLM contract** (`app/models/llm_schema.py`): turn schema gains an optional `requiere_tirada` (ability + band) in phase 1 and consumes a roll-result block in phase 2; creation schema gains the six attributes. `PROMPT_VERSION` bumps.
- **Prompts** (`app/services/prompts.py`): turn system prompt teaches the narrator when/how to call for a check and how to narrate honoring a given roll result; creation prompt teaches attribute generation; a new phase-2 resolution prompt is added.
- **Service** (`app/services/partida_service.py`): `avanzar_turno` / `avanzar_turno_stream` gain the two-phase flow and a server-side dice roller; modifier computation and result classification.
- **API** (`app/api/partidas.py`) and **frontend** (`partida-store.ts`, `turno-card.tsx`, a new dice-roll UI element, character-sheet display): surface the declared check, the roll, and the result tier; show the attribute block.
- **Frontend 3D** (new lazy-loaded dice-overlay component; `three` + `@react-three/fiber` dependencies): the animated d20 overlay, triggered by the `tirada` SSE event, with a `prefers-reduced-motion` static fallback. Three.js is kept out of the initial bundle via dynamic import.
- **Docs** (`docs/prompts.md`): changelog entry for the contract bump.
- No new external dependencies; the dice roller uses the standard library.
