---
name: work-on
description: Work on a GitLab issue tracker (#123) or merge request (!123), implement the requested changes, and maintain the linked MR, issue metadata, and issue status. Use when asked to implement or work on an issue or MR, not for read-only questions or reviews.
---

# Work on a GitLab issue or MR

Accept an issue reference such as `$work-on #123` or an MR reference such as `$work-on !123`, with any additional scope from the user. Resolve the project from the current repository or an explicitly supplied project. If the project or reference is ambiguous, clarify before modifying anything.

Read the available `glab` skill before running GitLab CLI or API commands.

## Workflow

1. Read the issue or MR, its discussions, and linked issue/MR context to establish the requested work.
2. For an issue, reuse an existing relevant open MR or open one for the implementation. For an MR, use its source branch as the basis for the work and identify its linked tracker; do not create a duplicate MR. Before editing, create and enter a new worktree dedicated to this task:
   - Prefer the current harness's supported worktree mechanism (for example, Claude Code or Codex), discovering its available tools or documented workflow rather than assuming commands. If the harness has already created a fresh worktree for this task, use it.
   - If no native mechanism is available, use `git worktree add` with a dedicated path and branch. Base new issue work on the project's target branch and existing MR work on the MR's current source branch tip.
   - Preserve other checkouts and uncommitted work. If the MR branch is already checked out elsewhere, use a separate local branch in the new worktree and explicitly push updates to the existing MR source branch; do not force checkout or create a duplicate MR.
   - Perform edits, checks, and commits in the new worktree, and report its path and branch with the result.
3. Implement the requested changes with minimal scope and run appropriate checks.
4. Use [gitlab-maintenance](../gitlab-maintenance/SKILL.md) to maintain the MR and linked tracker, verify the resulting metadata, and report the links and anything that could not be completed.
   - Include `Closes #<iid>` in the implementation MR description for a same-project issue (use a full issue URL for a cross-project closing reference). Verify the saved description contains it. If the user agrees to defer follow-up work, describe that separately; do not replace the closing reference with `Related to` or decide to keep the issue open unless the user explicitly requests that.
