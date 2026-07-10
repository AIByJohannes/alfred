---
name: codebase-research
description: Investigate a repository before proposing or making a change. Use for implementation, debugging, refactoring, architecture questions, and code review when the answer depends on current files, tests, commands, or runtime behavior.
---

# Codebase Research

1. Read the repository instructions and inspect the affected modules, their callers, and focused tests.
2. Use `Grep` or `CodeSearch` for text search. Include the relevant file and line evidence in conclusions.
3. Identify the smallest change that satisfies the request and preserves established contracts.
4. Implement with the repository's existing patterns. Do not read secret-bearing files or `.env*` files.
5. Run the focused test, check, or build command. State clearly when a required verification cannot run.
