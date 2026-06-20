## 1. Azure Foundry deployment & config

- [x] 1.1 Deploy `gpt-4o-mini-tts` in Azure Foundry and document the steps (deployment name, region, supported voices) in the setup/deployment docs
- [x] 1.2 Add `audio_deployment` setting to `app/core/config.py` (`AUDIO_DEPLOYMENT` env var)
- [x] 1.3 Add `AUDIO_DEPLOYMENT=gpt-4o-mini-tts` to `backend/.env.example`
- [x] 1.4 Update the `CLAUDE.md` env-var table and architecture notes to mention the TTS model and audio flow

## 2. Backend — Foundry client

- [x] 2.1 Add `generar_audio(texto, voice, *, response_format="mp3") -> bytes` to `app/services/foundry_client.py` using `audio.speech.create` with `model=settings.audio_deployment` and fixed Spanish steering `instructions`
- [x] 2.2 Wrap the call in `_with_retries` and emit telemetry via `record_llm_call`/`record_llm_error` with `operation="audio"`
- [x] 2.3 Raise `FoundryError` on failure / empty audio, consistent with the image methods

## 3. Backend — blob caching

- [x] 3.1 Add a deterministic audio blob name keyed by `(codigo, turno, voice)` under the `{codigo}/audio/` prefix (so `eliminar_imagenes` prefix-delete already cleans it up)
- [x] 3.2 Add audio helpers to `app/repositories/imagen_repo.py`: `subir_audio(...) -> url`, plus an existence/URL lookup for cache hits, with `content_type="audio/mpeg"`

## 4. Backend — voices, DTOs, service, endpoint

- [x] 4.1 Define the allowed narrator voices (allow-list/enum) and a default voice, shared as the server's source of truth
- [x] 4.2 Add the audio request DTO (`voice`, validated against the allow-list) and an `AudioTurnoResponse` (`audio_url`) to `app/models/domain.py`
- [x] 4.3 Add a service method to `app/services/partida_service.py` that loads the game, finds the turn (404 if absent), validates the voice, returns the cached audio URL on a hit, and otherwise synthesizes via `foundry.generar_audio(turno.narrativa, voice)`, uploads it, and returns the URL
- [x] 4.4 Add `POST /api/partidas/{codigo}/turn/{turno}/audio` to `app/api/partidas.py` returning `AudioTurnoResponse` (`{ audio_url }`)
- [x] 4.5 Map invalid-voice and missing-turn errors to the appropriate HTTP responses

## 5. Backend — tests

- [x] 5.1 Unit-test `generar_audio` (success + error paths, Spanish instructions passed) with the Foundry client mocked
- [x] 5.2 Test the service/endpoint: cache miss synthesizes + uploads + returns url; cache hit returns url and does NOT call the TTS model; unknown turn → 404 (no TTS call); invalid voice → error (no TTS call)
- [x] 5.3 Verify a different voice produces a separate cache entry and that deleting a game removes its audio blobs (covered by the `{codigo}/` prefix delete)

## 6. Frontend — voice preference in Settings

- [x] 6.1 Add `narratorVoice` (value + setter, persisted) to `src/store/settings-store.ts` with a default voice and a typed voice union
- [x] 6.2 Add a narrator-voice `OptionGroup` (or equivalent control) to `src/components/settings-sheet.tsx`
- [x] 6.3 Update settings-store/settings-sheet tests for the new voice preference and persistence

## 7. Frontend — API client & types

- [x] 7.1 Add types for the audio request/response (`{ audio_url }`) to `src/lib/types.ts`
- [x] 7.2 Add `generarAudioTurno(codigo, turno, voice)` to `src/lib/api.ts` (JSON `{ audio_url }`, like `generarImagenTurno`), sending the selected voice

## 8. Frontend — narrator card playback control

- [x] 8.1 Add a bottom-left play/stop control to the narrator card in `src/components/turno-card.tsx` with an accessible label/tooltip
- [x] 8.2 Implement lazy request on first play (fetch the audio URL), remember the URL per `(turno, voice)` to skip the round-trip on replay, and re-request when the voice changed
- [x] 8.3 Implement play/stop toggle via an `<audio>` element bound to the returned URL, plus loading and error feedback states
- [x] 8.4 Update `turno-card` tests: no audio request before play, request on first play, replay reuses the cached URL, error state surfaces and allows retry

## 9. Verification

- [x] 9.1 Backend: `ruff check .`, `ruff format .`, `pytest` all pass
- [x] 9.2 Frontend: `pnpm lint`, `pnpm typecheck`, and `pnpm gen:types` (regenerate API types) all pass
- [ ] 9.3 Manual smoke test: select a voice in Settings, press play on a turn, confirm Spanish audio plays, voice change produces new audio, replay is instant (cache hit), and no request fires before play — _requires the live `gpt-4o-mini-tts` deployment + browser; run after deploying._
