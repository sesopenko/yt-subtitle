# Repository Guidelines

## Project Structure & Module Organization

This directory currently contains no application code, tests, assets, or build configuration. Establish the layout when adding the first implementation, and update this guide to match it.

Keep source code, tests, and static assets in clearly named locations, such as `src/`, `tests/`, and `assets/`, when appropriate for the chosen stack. Keep project configuration at the repository root. Document the purpose of new top-level directories in `README.md`.

## Build, Test, and Development Commands

No build, test, or local development commands are configured yet. When introducing tooling, document exact installation, development, build, and test commands in `README.md`. Prefer project-managed scripts so contributors use consistent entry points. Do not assume commands such as `npm test` work until their configuration exists.

## Coding Style & Naming Conventions

No language, formatter, or linter has been selected. Follow the conventions of the chosen language and configure formatting and linting alongside the first source files. Use consistent indentation within each file, descriptive names, and small modules with clear responsibilities. Avoid unrelated formatting changes in functional patches.

## Testing Guidelines

No testing framework or coverage threshold is established. Add automated tests with the first testable behavior, document how to run them, and use the selected framework’s standard test naming pattern. Cover expected behavior, edge cases, and failures; add regression tests for bug fixes.

## Commit & Pull Request Guidelines

No Git history is available to establish commit conventions. Use concise, imperative commit subjects, such as `Add subtitle parser`, and keep commits focused.

Pull requests should describe the change, its motivation, and validation performed. Link relevant issues and include screenshots for visual changes. Explicitly identify checks that could not be run.

## Security & Configuration

Keep credentials and local configuration out of version control. Provide sanitized configuration examples and document required environment variables when configuration is introduced.
