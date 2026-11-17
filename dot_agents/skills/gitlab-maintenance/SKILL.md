---
name: gitlab-maintenance
description: Keep GitLab MR and issue details current when creating or modifying an MR or implementing changes linked to an existing MR or issue. Applies without work-on, including manually checked-out MRs. Excludes read-only questions and reviews.
---

# Maintain GitLab MRs and issues

Read the available `glab` skill before running GitLab CLI or API commands.

Resolve the project and relevant MR or issue from the current repository, branch, and task context. Read their descriptions, discussions, and links before updating them. If the target is ambiguous, clarify before modifying it. Work in the current checkout; this skill does not require a new worktree or authorize creating an MR, committing, pushing, merging, or closing issues.

## Workflow

1. Keep the MR description and linked issue details accurate for the final scope, including links and the issue-closing reference when the MR resolves the issue.
2. Assign the MR and tracker to Mr.Sklk, resolving his GitLab account rather than guessing the username.
3. Fill in missing details on the MR and linked tracker, including user-created or manually checked-out MRs. Set appropriate labels and an epic where supported and justified by the work. Discover the available values and IDs rather than inventing them. Preserve unrelated metadata and report unavailable or ambiguous fields. Select scheduling metadata as follows:
   - Milestone: choose the most relevant available milestone that is still open and not outdated, checking its dates against the current date. Do not hardcode a quarter or year.
   - Issue iteration: use the applicable existing iteration in the default cadence available to the project or group. Determine the default from available configuration or established usage; do not assume a custom cadence by name or create a new cadence. If no default can be identified unambiguously, report that limitation.
4. Once an MR is open for the tracker, set the issue status to `In Progress` using the procedure below. Do not regress a completed issue or reopen a closed issue.
5. Verify the resulting MR and tracker metadata, report the links and validation results, and identify anything that could not be completed. Opening or updating an MR does not imply merging it.

## GitLab issue status

Update status through `glab api graphql`. Substitute the discovered IDs in the examples below.

1. Get the issue's global numeric ID, not its project-local IID:

   ```sh
   glab api projects/:id/issues/<iid>
   ```

   Use the response's `id` in `gid://gitlab/WorkItem/<id>`.

2. Read the allowed statuses; never assume status IDs or capitalization:

   ```sh
   glab api graphql -f query='{
     workItem(id: "gid://gitlab/WorkItem/<id>") {
       workItemType {
         widgetDefinitions {
           ... on WorkItemWidgetDefinitionStatus {
             allowedStatuses { id name }
           }
         }
       }
     }
   }'
   ```

3. Select the returned status representing `In Progress` and use its exact ID. If no matching status is available, report that limitation instead of choosing another status.

   ```sh
   glab api graphql -f query='mutation {
     workItemUpdate(input: {
       id: "gid://gitlab/WorkItem/<id>",
       statusWidget: {status: "<status-global-id>"}
     }) {
       errors
       workItem {
         widgets {
           ... on WorkItemWidgetStatus {
             status { name }
           }
         }
       }
     }
   }'
   ```

4. Verify there are no GraphQL errors, `workItemUpdate.errors` is empty, and the returned status name matches the selected allowed status. Do not claim success otherwise.
