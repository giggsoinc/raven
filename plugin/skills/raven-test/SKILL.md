---
name: raven-test
description: Use when writing or reviewing tests. Forces test-first discipline —
  writes tests before implementation. Use when asked to implement a feature
  or fix a bug to ensure test coverage exists first.
allowed-tools: Read Write Edit Bash
---

# Raven-Test

## Test-first sequence
1. Read the function/module being tested
2. List all edge cases (empty input, None, max values, error states)
3. Write tests FIRST — before any implementation change
4. Run tests — confirm they fail (proving they test real behaviour)
5. Implement — make tests pass
6. Run tests again — all green

## Test standards
- Use pytest
- One assert per test where possible
- Test names: `test_{function}_{scenario}_{expected_outcome}`
- Mock external calls (S3, DB, APIs) — never hit real services in tests
- Coverage: happy path + at least 2 edge cases per function
