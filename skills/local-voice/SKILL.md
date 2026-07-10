---
name: local-voice
description: Generate local speech output with Kokoro-compatible text-to-speech tooling. Use when the user asks Alfred to read text aloud, synthesize narration, or configure local TTS.
compatibility: Requires a locally installed Kokoro-compatible TTS command or Python package.
---

# Local Voice

1. Ask for the text, preferred voice, output path, and format when they are not supplied.
2. Prefer a local Kokoro-compatible runtime and write audio beneath the active project or runtime artifacts directory.
3. Keep synthesis commands explicit about the selected voice and output file.
4. Verify that the generated file exists and report its path.
5. Do not transmit text to a remote TTS service unless the user explicitly asks for it.
