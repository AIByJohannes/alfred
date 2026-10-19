# TUI keyboard shortcuts

Alfred's TUI follows Claude Code where the same concepts exist. Behavior that
cannot be matched is listed explicitly instead of being silently ignored.

## Implemented

| Key | Behavior |
| --- | --- |
| `Enter` | Send the prompt. Ignored while a run is active. |
| `Esc` | Cancel the active run. With no run: clear input, then exit when empty. |
| `Ctrl+C` | Cancel the active run. Press again while cancelling to exit. With no run: clear input, then exit when empty. |
| `Ctrl+D` | Exit when the input is empty; otherwise delete one character. |
| `Ctrl+U` | Clear the input line. |
| `Ctrl+W` | Delete the previous word. |
| `Tab` | Complete a slash command or skill name. |
| `Up` / `Down` | Recall previous prompts; restore the draft after the newest entry. |
| `PageUp` / `PageDown` | Scroll the transcript by ten lines. |
| `/` | Show matching built-in commands and skills above the composer. |

## Slash commands

- `/skills` lists bundled, project, and user skills.
- `/<skill> [args]` runs a skill directly. Tab completion fills the name.
- `/new` starts a fresh conversation while keeping the system prompt.
- `/help` prints commands and shortcuts.
- `/quit` (or `/exit`) exits.

Skills are discovered from the current project and from `skills/`, plus
Cersei's bundled, `.claude`, and `.agents` locations.

Cancellation is cooperative: Cersei checks the cancel token between model turns,
so a tool that is already running may finish before the run stops. Alfred keeps
the run active until then and blocks new submissions, which prevents overlapping
edits. Press `Ctrl+C` a second time to force the process to exit. Cancelled or
failed turns stay visible in the transcript but are not persisted to the next
model request; the next prompt resumes from the last completed turn.

## Deliberate differences from Claude Code

| Claude Code behavior | Alfred behavior | Reason |
| --- | --- | --- |
| `Shift+Tab` cycles permission modes | Not bound | Alfred's coding tools currently use Cersei's `AllowAll` policy; there are no interactive permission modes to cycle. |
| `Ctrl+R` opens transcript/verbose history | Not bound | The TUI transcript is always visible; there is no separate verbose mode yet. |
| `Esc Esc` rewinds to an earlier message | Not implemented | Requires persisted turn checkpoints and a rewind UI. |
| `Ctrl+L` clears the terminal | Not bound | The transcript is redrawn on every tick; clearing the screen has no lasting effect. |
| Multi-line `Shift+Enter` composer | Not supported | The composer is intentionally single-line; use the web workbench for long multi-line prompts. |
| Mouse selection/copy modes | Terminal-native only | Alfred keeps the terminal's normal selection behavior rather than enabling mouse capture. |

Update this document whenever a shortcut is added or a difference is removed.
