# Mode: checkpoint

Updates the active plan after completing work.

1. Ask (or infer): which tasks finished? Any surprises or decision changes?
2. Read the current plan file
3. Tick completed items: `- [ ]` → `- [x]`
4. Append to Progress Log:
   `- YYYY-MM-DD: Completed <X>. <Surprises>. <Decision changes>. Next: <what's up>.`
5. If a decision changed, update `## Decisions Made` and note it in the log
6. If all items ticked, set **Status** to `✅ Complete`
7. If any code was changed this session, remind: "Run `/sync-docs` before committing."
   TailorAI has domain CLAUDE.md files (agents/, api/, glassresumatch-ai/, etc.) —
   sync-docs knows which to update based on what files changed.
