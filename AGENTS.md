# Repository instructions

For video creation requests that invoke create-video, read `.agents/skills/create-video/SKILL.md` in this checkout and resolve its scripts and templates relative to that directory. The bundled copy includes the scripts, voice standards, and delivery workflow. Check runtime dependencies and model availability separately in each environment.

## Chat-context compression

- “Compress context” is a ChatGPT product control, not a repository command. Do not claim that an `AGENTS.md` instruction can trigger it, verify its percentage, or repair a non-responsive UI control.
- After compression, the messages visible in the chat normally remain visible. The operation only replaces older model working context with a summary; it is not a history deletion feature.
- If the displayed usage percentage does not change, treat it as an unverified UI or service-state issue. Ask the user to close and reopen the menu, refresh once, and report the result; do not advise repeatedly clicking the control.
- Preserve durable, task-critical facts in repository files (for example this `AGENTS.md`, a README, or a project note), rather than relying on an unobservable chat-context state.
