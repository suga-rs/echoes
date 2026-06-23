## 1. Dice core (pure, test-first)

- [x] 1.1 Write failing unit tests for the band→DC map (`trivial`=5, `facil`=10, `media`=15, `dificil`=20, `heroica`=25)
- [x] 1.2 Write failing unit tests for the d20 roller with an injectable `random.Random` (deterministic under seed)
- [x] 1.3 Write failing unit tests for tier classification: total≥DC→`exito`, total<DC→`fracaso`, nat-20→`exito_critico`, nat-1→`fracaso_critico` (overrides win)
- [x] 1.4 Write failing unit tests for the ability modifier `floor((score−10)/2)` across edge scores (3, 7, 10, 16, 18)
- [x] 1.5 Implement the dice/check helper module (band map, roller, classifier, modifier) until 1.1–1.4 pass

## 2. Domain model + backward compatibility

- [x] 2.1 Write failing tests: legacy `Personaje` (no `atributos`) deserializes with all six abilities = 10 (+0); legacy `TurnoHistorial` (no `tirada`) deserializes as `None`
- [x] 2.2 Add `Atributos` model (six ints 3–18, defaults 10) to `domain.py` and attach `atributos` to `Personaje`
- [x] 2.3 Add the optional `tirada` record (habilidad, banda, dc, d20, modificador, total, resultado) to `TurnoHistorial`, default `None`
- [x] 2.4 Confirm 2.1 passes and existing partida-serialization tests stay green

## 3. LLM contract: creation attributes

- [x] 3.1 Write failing test: `CREACION_JSON_SCHEMA` requires the six attributes (3–18) and `CreacionLLMResponse` parses them
- [x] 3.2 Extend `CREACION_JSON_SCHEMA` and `PersonajeLLM` with the six ability scores
- [x] 3.3 Update `SYSTEM_PROMPT_CREACION` / creation user-prompt to generate attributes biased to the player's description and genre
- [x] 3.4 Map generated attributes into `Personaje.atributos` in `crear_partida`; assert via test

## 4. LLM contract: two-phase turn

- [x] 4.1 Write failing tests for the phase-1 turn schema: optional `requiere_tirada = {habilidad ∈ 6 enum, banda ∈ 5 enum}`, absent when no check
- [x] 4.2 Extend `TURNO_JSON_SCHEMA` / `TurnoLLMResponse` for phase 1 (`requiere_tirada`) and add the phase-2 resolution schema/model (narrativa, opciones, state/arc updates honoring a given tier)
- [x] 4.3 Update `SYSTEM_PROMPT_TURNO` with the "declare a check vs trivial/impossible ⇒ no check" rules, the six-ability mapping guidance, and few-shot examples
- [x] 4.4 Add `SYSTEM_PROMPT_RESOLUCION` (phase 2): narrate honoring the result tier; add `build_resolucion_user_prompt` injecting habilidad, DC, d20, modificador, total, resultado
- [x] 4.5 Bump `PROMPT_VERSION` and add a `docs/prompts.md` changelog entry

## 5. Service orchestration (both turn paths)

- [x] 5.1 Write failing tests for `avanzar_turno`: unchecked action → single call, no `tirada`; checked action → roll + second call, `tirada` persisted with correct tier (inject a seeded roller and a fake Foundry)
- [x] 5.2 Implement the two-phase flow in `avanzar_turno`: phase-1 declaration → shared roll/classify helper → phase-2 resolution → persist `tirada` on the turn
- [x] 5.3 Factor roll + classification into a shared helper used by both turn paths
- [x] 5.4 Implement parity in `avanzar_turno_stream`: resolve phase 1 before streaming, emit a `tirada` SSE event before the `token` stream, then stream phase-2 narrativa; persist `tirada`
- [x] 5.5 Write failing test for the stream path asserting the `tirada` event precedes tokens and the turn persists the roll

## 6. API + frontend surfacing

- [x] 6.1 Extend `TurnoResponse` / start + resume payloads to carry the `tirada` block and the character's `atributos`
- [x] 6.2 Add `tirada` and `atributos` to `frontend/src/lib/types.ts` (and regenerate types if backend running)
- [x] 6.3 Extend `partida-store.ts` to hold attributes and per-turn roll data, including the stream `tirada` event
- [x] 6.4 Render the resolved check as a static staged-reveal element in `turno-card.tsx` (ability, band/DC, d20, modifier, total, result tier); show nothing on unchecked turns — this is also the reduced-motion fallback
- [x] 6.5 Display the six-attribute stat block with modifiers in the character UI
- [x] 6.6 Add/adjust frontend tests for the roll display and stat block

## 7. 3D dice roll animation (frontend)

- [x] 7.1 Add `three` as a dependency (no physics engine; r3f tried then dropped — its reconciler fails on React internals under the Next bundler, so vanilla three.js is used)
- [x] 7.2 Build the precomputed face→quaternion lookup for the d20 icosahedron (deterministic; unit-tested that each face maps to a distinct camera-facing orientation)
- [x] 7.3 Build the procedural icosahedron d20 mesh that settles on the rolled face (per-face number texture atlas deferred to the design open question; the value is surfaced in the staged reveal)
- [x] 7.4 Implement the tumble + settle animation that comes to rest on the server-rolled face (lerp to the face's quaternion)
- [x] 7.5 Implement the staged reveal (d20 → modifier → total → DC compare → verdict) and crit treatments (gold nat-20, red nat-1)
- [x] 7.6 Mount as a full-screen overlay reusing the Radix Dialog pattern from `imagen-modal.tsx`; trigger on the `tirada` SSE event so it overlaps phase-2 latency; auto-dismiss into the narration
- [x] 7.7 Lazy-load via `next/dynamic(..., { ssr: false })`; wire the `prefers-reduced-motion` / load-failure path to the static element from 6.4
- [x] 7.8 Add frontend tests asserting the animation receives and renders the server roll data (assert data, not pixels) and that the reduced-motion path renders the static fallback

## 8. Verification

- [x] 8.1 Run `pytest`, `ruff check .`, `ruff format .` in `backend/` — all green (188 passed, 79% cov)
- [x] 8.2 Run `pnpm lint`, `pnpm typecheck`, and frontend tests in `frontend/` — all green (53 passed)
- [ ] 8.3 Manual smoke: create a game (attributes present), take a trivial action (no roll), take a risky action (3D roll plays, settles on the server value, narration honors tier), reload a legacy partida (neutral stats, still playable) — REQUIERE stack vivo con Azure
- [ ] 8.4 Manual smoke with reduced motion enabled: the static fallback shows the same values and no animation — REQUIERE stack vivo
- [x] 8.5 Confirm Three.js is not in the initial bundle (loads only on first check) — `pnpm build`: ruta `/` First Load JS 177 kB, three en chunk lazy
- [x] 8.6 Run `openspec validate add-d20-skill-checks --strict` and resolve any issues — valid
