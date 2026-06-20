## Context

Echoes narrates a branching story turn by turn. The narrator text is shown in the
turn card and is currently read-only. Image generation already establishes the
project's pattern for on-demand, per-turn AI media: the frontend calls a
`POST /api/partidas/{codigo}/turn/{turno}/image` endpoint, the service orchestrates
a Foundry call, and the result is persisted to Blob Storage and cached on the turn.

This change adds spoken narration through a new Azure Foundry text-to-speech model
(`gpt-4o-mini-tts`). Audio is generated lazily (only when the player presses play)
and then **cached in Blob Storage and served by URL**, closely mirroring the
existing image flow. Because the narrator text (`turno.narrativa`) is already
Spanish per the `spanish-output-contract`, narration is always synthesized in
Spanish; the model is additionally steered to Spanish so the accent/pronunciation
is correct regardless of the chosen voice.

Constraints:
- Reuse the existing `openai` Azure client and Entra-ID/API-key auth path in
  `FoundryClient`; no new dependencies.
- Reuse the existing Blob Storage account/container; audio lives under the
  per-game `{codigo}/audio/` prefix so the existing `eliminar_imagenes`
  prefix-delete already cleans it up on game deletion.
- Voice selection is a player preference that belongs in the existing Settings
  panel and `settings-store` (localStorage-persisted), like font/size.
- Synthesis must be lazy — triggered only by the player pressing play, and only
  on a cache miss for that turn + voice.

## Goals / Non-Goals

**Goals:**
- Lazy, per-turn TTS: synthesize only when the player presses play on a turn and
  only on a cache miss for that turn + voice.
- Cache generated audio in Blob Storage (keyed by turn + voice) and serve it by
  URL; reuse it on later plays, including across reloads.
- Narration always in Spanish, with the model steered to Spanish regardless of
  the selected voice.
- A play/stop control at the bottom-left of the narrator card with loading/error
  states.
- A persisted narrator-voice preference selectable in Settings, sent with each
  audio request.
- A backend endpoint + Foundry client method for on-demand synthesis + caching,
  plus the Azure Foundry deployment steps for `gpt-4o-mini-tts`.

**Non-Goals:**
- Auto-play, word-level highlighting/karaoke, or playback queueing across turns.
- A per-game audio cap (images have one; audio does not in this change).
- Streaming partial audio while synthesizing (we deliver the full clip).
- Per-voice translation of the narrative (text is already Spanish; we only set the
  spoken language).

## Decisions

### Decision: Cache audio in Blob Storage, keyed by turn + voice, serve by URL
On a play request the service computes a deterministic blob name from
`(codigo, turno, voice)` — e.g. `{codigo}/audio/turno-{turno:03d}-{voice}.mp3`. If
that blob already exists, the endpoint returns its URL without calling the TTS
model. On a miss, it synthesizes the turn's narrative, uploads the clip, and
returns the new URL. The endpoint responds with `{ audio_url }` (JSON), and the
browser plays the blob URL directly — exactly like the image flow.

- **Why:** Re-synthesizing on every play (or reload) wastes TTS cost and adds
  latency. A deterministic, voice-scoped blob name makes cache hits a cheap
  existence check, persists across sessions, and — because audio sits under the
  per-game `{codigo}/` prefix — is already cleaned up by `eliminar_imagenes` when
  the game is deleted. Reusing the images container avoids new infra.
- **Cache key includes voice:** Different voices are different clips, so the voice
  is part of the blob name. Switching voices produces a separate cache entry;
  switching back is a hit.
- **No URL stored on the Partida document:** Because a turn can have multiple
  cached voices, a single `audio_url` field on `TurnoHistorial` can't represent
  the set. Deterministic naming + an existence check avoids a schema change and a
  multi-voice map; the cost is one cheap blob `exists()` call per play.
- **Alternative considered (rejected):** Transient binary response with no
  persistence. Rejected per the explicit caching requirement — it re-cost on every
  reload and replay.
- **Client-side caching:** The frontend still remembers the returned URL per
  `(turno, voice)` in component state to skip the endpoint round-trip on in-session
  replays; a voice change just requests the new URL.

### Decision: Narration is always Spanish
The input text is already Spanish (`spanish-output-contract`). To guarantee the
spoken output matches, `generar_audio` passes a fixed Spanish steering
`instructions` to `gpt-4o-mini-tts` (e.g. narrate in neutral/rioplatense Spanish)
so accent and pronunciation are Spanish for every voice.

- **Why:** The selectable voices are language-agnostic; without steering, a voice
  could render Spanish text with a foreign accent. A fixed instruction keeps the
  language a system invariant, not a per-player choice.
- **Alternative considered (rejected):** Trusting the input text alone to
  determine pronunciation. Rejected as less reliable across voices.

### Decision: Voice is chosen client-side, validated server-side
The selected voice lives in `settings-store` (persisted) and is sent in the audio
request body. The backend validates the voice against an allow-list of the
model's supported voices and rejects unknown values, falling back to / defaulting
a sensible voice.

- **Why:** Matches the existing preference pattern (font/size) and keeps the
  player in control, while the server stays authoritative about what the model
  accepts.
- **Alternative considered (rejected):** Hardcode a single voice — fails the
  explicit requirement for a Settings voice option.

### Decision: New `generar_audio` method on `FoundryClient`
Add `generar_audio(texto, voice, *, response_format="mp3") -> bytes` using the
Azure OpenAI `audio.speech.create` API with `model=settings.audio_deployment` and
a fixed Spanish `instructions`. Wrap the call in the existing `_with_retries`
(transient-error backoff) and emit telemetry via
`record_llm_call`/`record_llm_error` with `operation="audio"`, consistent with
`chat`/`image`.

- **Why:** Reuses the established retry, auth, and telemetry plumbing; one new
  method parallels `generar_imagen`.

### Decision: Endpoint and service shape mirror the image flow
- Route: `POST /api/partidas/{codigo}/turn/{turno}/audio`, body carries `voice`.
- `PartidaService` loads the game, finds the turn (404 if absent), validates the
  voice, checks the blob cache, and on a miss calls
  `foundry.generar_audio(turno.narrativa, voice)` and uploads the result; the
  route returns `{ audio_url }` (parallel to `ImagenTurnoResponse`).
- **Why:** Familiar layering (API → service → foundry → blob repo); validation of
  game/turn reuses existing repo lookups and error types, and `{ audio_url }`
  matches the image response contract the frontend already understands.

### Decision: Config + env var for the TTS deployment
Add `audio_deployment` to `Settings` and `AUDIO_DEPLOYMENT` to `backend/.env.example`
and the `CLAUDE.md` env table, alongside `LLM_DEPLOYMENT`/`IMAGE_DEPLOYMENT`.
Document the Azure Foundry deployment steps for `gpt-4o-mini-tts`.

### Decision: Frontend playback via a single HTMLAudioElement per card
On first play, request the audio URL from the endpoint and play it through an
`Audio` element (or `<audio src=audio_url>`) held in the card. The control toggles
play/stop and reflects loading and error states (parallel to the image control's
feedback states). The returned URL is remembered per `(turno, voice)` to skip the
round-trip on in-session replays.

## Risks / Trade-offs

- **Cost/abuse: no per-game cap on synthesis** → Lazy generation bounds it to
  explicit intent, and blob caching means each `(turno, voice)` is synthesized at
  most once ever. A cap or rate limit can be added later if usage warrants.
- **Blob proliferation: one clip per turn × per voice tried** → Bounded by the
  small voice list and actual play behavior; all clips share the `{codigo}/`
  prefix and are deleted with the game. A cap on distinct voices per game could be
  added if needed.
- **Stale cache if narrative text could change** → Narrative history is immutable
  after a turn is recorded, so a turn+voice clip never goes stale. If that ever
  changes, the blob name would need a content hash.
- **Latency: long narration = slow synthesis, no streaming** → Only on a cache
  miss; show a clear busy state. Clips are per-turn (bounded by `max_tokens`
  narrative length), so duration is modest, and subsequent plays are instant.
- **Voice list drift between client and model** → Keep a single allow-list of
  voices on the backend as the source of truth; the frontend's options should
  match it. Server validation rejects mismatches instead of failing opaquely, and
  the voice is part of the blob name so an invalid voice can't poison the cache.
- **Public blob URL exposure** → Audio URLs are directly fetchable like image
  URLs; this matches the existing trust model for game media (non-sensitive,
  per-game prefixed).

## Migration Plan

1. Deploy `gpt-4o-mini-tts` in Azure Foundry; note the deployment name.
2. Set `AUDIO_DEPLOYMENT` in backend environment(s); update `.env.example`.
3. Ship the backend (new method + endpoint + blob caching + config) — backward
   compatible, no Cosmos schema/data migration; reuses the existing images
   container (no new container needed).
4. Ship the frontend (play control + voice setting).
- **Rollback:** Hide/disable the play control on the frontend; the endpoint is
  additive and can stay. Unsetting `AUDIO_DEPLOYMENT` disables synthesis.

## Open Questions

- Final default voice and the exact set of voices to expose in Settings (pending
  confirmation of the voices `gpt-4o-mini-tts` supports in the target region).
- Audio format to request (`mp3` vs `opus`/`aac`) — default to `mp3` for broad
  browser support unless size/latency argues otherwise.
