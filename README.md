# SubLoka

> Focused offline bilingual caption editor for Android (English ↔ Indonesia).

Current implementation is a **frontend demo shell**. Caption generation, translation, media decoding, persistence, and export engines are intentionally not connected yet. Demo states are labeled in the UI and must not be interpreted as real inference.

## Product direction

`Choose video → Generate caption → Correct → Export`

Editor workspaces are deliberately limited to **Caption**, **Timing**, and **Style**. Translation is contextual state/action, not a fourth workspace.

## Toolchain baseline

- Android Gradle Plugin: 9.4.0
- Gradle wrapper target: 9.6.0
- Kotlin / Compose compiler plugin: 2.3.21
- compileSdk / targetSdk: 37
- minSdk: 26
- Compose BOM: 2026.09.00
- Activity Compose: 1.13.0
- Core KTX: 1.19.1

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

## Build

A standard Gradle wrapper properties file is included, but the wrapper JAR/scripts are not generated in this execution environment because Android/Gradle distributions are unavailable locally. In Android Studio, open the project and use the IDE-provided Gradle tooling, or generate the wrapper with Gradle 9.6.0:

```bash
gradle wrapper --gradle-version 9.6.0
./gradlew :app:assembleDebug :app:lintDebug
```

Do not mark T04–T07 `DONE` until those commands and relevant UI tests pass. See `.agents/plan.md` and `.agents/testing.md`.
