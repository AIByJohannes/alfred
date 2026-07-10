---
name: image-generation
description: Generate or edit images with a local model or an explicitly configured Black Forest Labs API. Use when the user asks Alfred to create, transform, or prepare visual assets.
compatibility: Requires a local image-generation runtime or user-configured BFL API credentials.
---

# Image Generation

1. Identify whether the request is generation or an edit and preserve any supplied source asset.
2. Prefer local generation when it is configured; use the BFL API only when the user has explicitly configured and selected it.
3. Write generated assets to a clear output path and avoid overwriting a source image.
4. Record the prompt, model choice, and output path with the session artifacts when available.
5. Verify the output file exists before presenting it as complete.
