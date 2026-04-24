Archived from `.cursor/plans/REPO_TRUST_RESTORATION_PLAN.md` on 2026-04-23 so this historical trust-restoration plan is visible to all agents.

# Repo Trust Restoration Plan (Historical)

This archived plan reflects an older repo shape in which the active scanner project was described as `global-macro-scanner/` under an outer monorepo shell. It is retained as historical context only and should not be treated as current structure guidance.

## Original summary

Restore confidence in the repository by making the outer git root clearly behave as a monorepo shell and the inner `global-macro-scanner/` clearly behave as the only active Python scanner project.

## Original focus areas

- Clarify root vs scanner-subtree ownership
- Standardize environment and dependency ownership
- Clean up git-facing noise safely
- Verify canonical script taxonomy
- Enforce clean Python execution boundaries
- Finish with a repository-shape pass
