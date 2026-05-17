# Repository Boundaries

TypeUp is split across three repositories. Keep this backend repository focused on cloud business logic and model proxying.

## This Repository: TypeUp Backend

Owns:

- User registration, login, access tokens, and refresh token rotation.
- Plans, orders, payments, and entitlement activation.
- Usage metering and quota enforcement.
- STT and LLM proxy APIs.
- Provider credentials such as GLM and Alipay keys.
- Admin APIs for account and entitlement operations.
- Consistent API error responses.

Should not own:

- Electron UI, local desktop state, or desktop packaging.
- Microphone capture, hotkey monitoring, native typing, or local engine UI.
- Platform-specific macOS/Windows/Linux permission workflows.

## Desktop Client: `oxygen0827/typeup-win`

The desktop client owns Electron, React UI, local bridge, local settings, and desktop packaging. It should call this backend through stable `/v1` APIs and should not embed payment or entitlement policy.

Backend errors should remain structured so the desktop app can branch on `error.code` and display `error.message`.

## Engine: `wangqioo/voice-keyboard`

The engine owns local voice input behavior:

- Recording, PTT/VAD, microphone selection.
- Global hotkeys and keyboard/mouse monitoring.
- Typing text into the active application.
- Local STT/LLM provider adapters.
- Platform permissions and native helper UI.

The backend should not depend on engine internals. It only needs to accept standard STT/LLM API requests from authenticated clients.

## API Contract Rules

- Keep public client APIs under `/v1`.
- Return the unified error envelope for all JSON errors.
- Enforce entitlement and quota on the backend, not in the desktop client.
- Keep provider secrets on the backend. Desktop clients should only hold TypeUp tokens.
- Add tests when changing auth, billing, entitlement, quota, or model proxy behavior.
