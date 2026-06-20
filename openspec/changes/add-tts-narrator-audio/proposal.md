## Why

The narrator text is currently read-only, which excludes players who prefer or
rely on listening (accessibility, multitasking, immersion). Adding spoken
narration via a text-to-speech model makes the experience audible without forcing
audio cost on every turn — it is generated only when a player asks to hear it.

## What Changes

- Add a new Azure Foundry model, `gpt-4o-mini-tts`, used to synthesize speech
  from a turn's narrator text.
- Add a **play audio** control to the narrator (turn) card, anchored at the
  bottom-left of the card.
- Generation is **lazy**: the TTS API is only called when the player activates
  the play control for a turn (not at turn time, not eagerly) and only on the
  first play for a given turn + voice.
- Narration is always synthesized in **Spanish (rioplatense)**, consistent with
  the `spanish-output-contract`. The narrator text is already Spanish; synthesis
  steers the model to speak Spanish regardless of which voice is chosen.
- Generated audio is **cached in Blob Storage** (keyed by turn + voice) and
  reused on subsequent plays — including across reloads — instead of being
  re-synthesized. A game's audio is removed when the game is deleted.
- Add a **narrator voice** option in the Settings panel so the player chooses
  which voice the model uses; the choice persists locally and is sent with each
  audio request.
- Add backend support: a new audio-generation method on the Foundry client, a new
  endpoint that returns a turn's (cached or freshly synthesized) audio on demand,
  blob persistence for the audio, and a config/env var for the TTS deployment.
- Add Azure Foundry deployment steps for the new `gpt-4o-mini-tts` model to the
  setup documentation.

## Capabilities

### New Capabilities
- `narrator-audio`: On-demand (lazy) text-to-speech narration of a turn's text —
  the bottom-left play/pause control on the narrator card, the backend audio
  generation contract, and the player-selectable narrator voice preference.

### Modified Capabilities
- `reading-preferences`: The settings surface now also exposes a narrator **voice**
  control alongside the existing appearance controls (font, size, theme).

## Impact

- **Backend**
  - `app/core/config.py`: new `audio_deployment` (and any TTS-related) settings.
  - `app/services/foundry_client.py`: new `generar_audio` method (Azure OpenAI
    `audio.speech.create`), steering the model to Spanish.
  - `app/repositories/imagen_repo.py`: blob upload/existence helpers for audio,
    stored under the existing images container with the `{codigo}/audio/` prefix
    so per-game cleanup (`eliminar_imagenes`) already covers it.
  - `app/api/partidas.py`: new `POST /api/partidas/{codigo}/turn/{turno}/audio`
    endpoint returning the audio URL (cached or freshly synthesized) for that turn.
  - `app/services/partida_service.py`: orchestration to check the cache, synthesize
    the turn's narrative with the requested voice when absent, upload it, and
    return the URL.
  - `app/models/domain.py`: request/response DTO(s) for the audio endpoint
    (`voice` in, `audio_url` out).
  - `backend/.env.example`: `AUDIO_DEPLOYMENT` entry.
- **Frontend**
  - `src/lib/api.ts` + `src/lib/types.ts`: new audio endpoint client (returns
    `{ audio_url }`) + types.
  - `src/components/turno-card.tsx`: bottom-left play/pause control that lazily
    requests the audio URL and plays it via an `<audio>` element, with
    loading/error states.
  - `src/store/settings-store.ts` + `src/components/settings-sheet.tsx`: voice
    preference (state, persistence, settings control).
  - `frontend/.env.local.example`: if any new public var is needed.
- **Docs / Ops**
  - `CLAUDE.md` env-var table + architecture notes.
  - Deployment docs: steps to deploy `gpt-4o-mini-tts` in Azure Foundry.
- **Dependencies**: reuses the existing `openai` Azure client; no new packages
  expected.
