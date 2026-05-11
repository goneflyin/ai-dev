# Purpose of this project/directory

- This directory is the development workspace for coding delegated by Hermes.
- All tools built or maintained here should be kept in their own subdirectory.
- Each subdirectory is an independent project with its own README, tests, and Makefile.

# Project Structure

```
review-dashboard/    # gBrain Review Dashboard — web server + embedded frontend
braindump/           # Cross-session summarizer
gbrain/              # Read-later sync & pipeline utilities
skills/              # Hermes agent skill definitions
```

# Guidelines

## General

- All work done here should be done in a robust manner by ensuring it works and has well-written automated tests and specs.
- Write specs using Gherkin, and implement the steps in whatever manner is most effective and efficient.
- Before concluding any tasks:
  - Ensure any tests that might have been affected still work
  - Review all relevant tests and make sure they are clean and updated
  - If the automated specs are not sufficient, smoke test the project to ensure it works

## Installation

Each project has a `Makefile` with standard targets:

- `make install` — Copies files to their target location (e.g. `~/gbrain/`, `~/.hermes/skills/`)
- `make check` — Runs basic import/syntax checks
- `make test` — Runs the test suite (if implemented)

Always run `make check` (at minimum) and verify the tests pass after making changes.

## Adding New Projects

To add a new tool or project to this repository:

1. Create a new subdirectory
2. Add source files, README.md, and a Makefile with at least `install` and `check` targets
3. If the tool has tests, include them and add a `test` target to the Makefile
4. Update the root README.md with a brief description

## Submitting Completed Work

When a coding task is complete:

1. Ensure all tests pass
2. Run `make install` from the project directory to deploy
3. Commit and push all changes to github.
4. Report back to Hermes with a summary of what was done and the test results
