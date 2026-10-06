# SubLoka

> Focused offline bilingual caption editor for Android (English ↔ Indonesia).

Current implementation is a **frontend demo shell**. Caption generation, translation, media decoding, persistence, and export engines are intentionally not connected yet. Demo states are labeled in the UI and must not be interpreted as real inference.

## Product direction

`Choose video → Generate caption → Correct → Export`

Editor workspaces are deliberately limited to **Caption**, **Timing**, and **Style**. Translation is contextual state/action, not a fourth workspace.

## Toolchain baseline

- Android Gradle Plugin: 9.4.0
- Gradle Wrapper: 9.6.0
- Kotlin / Compose compiler plugin: 2.3.21
- compileSdk / targetSdk: 37
- minSdk: 26
- Compose BOM: 2026.09.00
- Activity Compose: 1.13.0
- Core KTX: 1.19.1

## Verification status

Android CI has verified the frontend scaffold on GitHub Actions:

- project guardrail validator: **PASS**
- `:app:assembleDebug`: **PASS**
- `:app:lintDebug`: **PASS**
- Gradle Wrapper 9.6.0 generation: **PASS**
- verified build evidence: [Android CI run #9](https://github.com/ferdilpu-sudo/Subloka/actions/runs/37462634099)
- wrapper bootstrap evidence: [Bootstrap Gradle Wrapper run #1](https://github.com/ferdilpu-sudo/Subloka/actions/runs/37463131375)

This proves the current frontend compiles and passes lint. It does **not** prove install/startup, interaction behavior, IME/adaptive layout, accessibility, media processing, offline inference, persistence, or real export. Those remain separate gates in `.agents/testing.md`.

## Modules

- `app` — composition root, navigation state, demo fixtures.
- `core:domain` — UI-facing product models and invariants used by the demo.
- `core:designsystem` — SubLoka theme and reusable semantic UI pieces.
- `feature:projects` — Projects, New Project, offline model setup, processing states.
- `feature:editor` — Caption/Timing/Style editor workspaces and adaptive composition.
- `feature:export` — final export choices and blocked-state explanation.
- `.agents` — coding-agent source of truth: product, rules, architecture, design, plan, testing, and handoff notes.

## Coding-agent guidance

All implementation guidance and handoff notes live under [`.agents/`](.agents/README.md). Agents should start at [`.agents/AGENTS.md`](.agents/AGENTS.md) and follow the prescribed read order before changing code. Keep task status in `.agents/plan.md` and test evidence in `.agents/testing.md`; do not scatter new planning Markdown around the repository.

## Build locally

Gradle Wrapper 9.6.0 is committed to the repository. A global Gradle installation is **not required**.

Windows PowerShell:

```powershell
git pull origin main
.\gradlew.bat --version
.\gradlew.bat :app:assembleDebug :app:lintDebug
```

macOS/Linux:

```bash
git pull origin main
./gradlew --version
./gradlew :app:assembleDebug :app:lintDebug
```

The first wrapper run downloads Gradle 9.6.0 automatically, so network access is required once unless the distribution is already cached.

T04 is **DONE** for scaffold/build/lint. T05–T07 remain **IMPLEMENTED** until relevant UI runtime tests and CP3 review are complete. See `.agents/plan.md` and `.agents/testing.md`.
