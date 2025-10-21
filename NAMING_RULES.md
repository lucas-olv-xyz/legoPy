# GP.5.1 Gotcha! File Naming Rules

Naming stays consistent across productions so editors can search, reuse and archive assets quickly. Use this cheat sheet whenever you add folders or export new media.

## Folders & Projects
- Pattern: `<ProjectPrefix><ProductionID>_<FOLDER_TYPE>_<Production name>`.
- Project prefix: single letter identifying the franchise (`G`, `Z`, etc.).
- Production ID: zero-padded number assigned before pre-production (`001`, `079`, `343`…).
- Folder type keywords separate deliverable stages (`MEDIA`, `PROJECTS`, `TEST`, `FINAL`).
- Trailing description is the plain-language topic (e.g., `I was adopted by a Billionaires family`).

## Video Parts
- Core pattern: `ProjectProductionID_<Situation>_<Quality>_<Language>[_Extra]`.
- Situation block captures the type and number: `H` Hook, `I` Intro, `T` Tip, `O` Outro. Each letter counts from `1` (e.g., `H1`, `H2`, `T1`…).
- Lowercase suffix (`T1a`, `H3b`) marks alternate edits—only one is used per video. Decimals split long parts sequentially (`T1.1`, `T1a.2b`).
- Bracketed refs show source footage: `T9(T1)` is a new part derived from `T1`; `H(T1)` means a tip promoted to hook.
- Dual-sided videos append pair tags like `R/P`, `H/C`, `L/U`; order matters if both appear sequentially (`PR`, `RP`).
- Situation combos allow plus signs and parentheses (`H1+I1`, `H(H1+I1)`) when the footage already implies a paired intro.

## Video Sequences
- Pattern: `ProjectProductionID_<VersionBlock>_<Quality>_<Language>[_Extra]`.
- Version block starts with permutation id (`V0`, `V1`, `C1`…), followed by chosen Hook (`H0`, `H1a`, …) and optional Intro (`I0`, `I1b` …). Omit `I0` entirely if no intro was filmed for that production.
- `V0` reflects the scripted order. Higher numbers document testing permutations (see the “Testing” sheet).
- Suffix after language captures additional context (topic, experiment name, etc.).

## Quality & Language Codes
- Export quality: `F` Final (3840×2160 @ 50 fps / 40 Mbps), `R` Reuse (1920×1080 @ 50 fps / 16 Mbps), `T` Test (1920×1080 @ 50 fps / 6 Mbps), `I` Internal (1280×720 @ 50 fps / 5 Mbps).
- Language matches the voice-over track (`EN`, `DE`, `IT`, `JP`, `RU`, `NoVO`, …).

## Edge-Case Reminders
- Preserve letter case: `H3a` ≠ `H3A`. Lowercase variants stay lowercase; uppercase variants are distinct and meant to pair (e.g., `T8A` with `T8B`).
- If a hook filename bundles intro tokens (`H1+I1`), treat it as a combined asset—wrap it as `H(H1+I1)` and append `I0` when no separate intro exists.
- Skip writing `_I0` in sequence names when a production has no intro footage at all.
- When building 2-minute exports, never mix lowercase variants (`T8a` vs `T8b`), but allow uppercase pairs (`T8A`, `T8B`) to follow one another.
