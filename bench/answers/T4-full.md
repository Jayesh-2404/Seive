Maximum steps for this agent have been reached, so this is a text-only response.

Pull request attention states are computed in **`src/lib/activity-model.ts`** by the function **`inferAttention(pull: PullRequest | null): AttentionState`**.

Order of precedence:
1. `!pull` → `"no-pull-request"`
2. `pull.draft` or `pull.reviewState === "draft"` → `"draft"`
3. `pull.checkState === "failure"` → `"checks-failing"`
4. `pull.reviewState === "changes_requested"` → `"agent-revising"`
5. `pull.reviewState === "approved"` → `"approved"`
6. `pull.reviewState === "in_review"` → `"in-review"`
7. `pull.reviewState === "ready"` → `"your-review"`
8. otherwise → `"unknown"`

The underlying `reviewState` and `checkState` values come from the server-side loader **`loadRepository`** in **`src/app/api/github/dashboard/route.ts`**, where `reviewState` is set as:

```ts
pull.draft ? "draft"
  : states.includes("CHANGES_REQUESTED") ? "changes_requested"
  : pull.requested_reviewers.length > 0 ? "in_review"
  : states.includes("APPROVED") ? "approved"
  : "ready"
```

Work items are sorted in **`src/lib/activity-model.ts`** by the function **`sortWorkItems(items: WorkItem[]): WorkItem[]`** in this order:

1. `needsYou` (`true` first)
2. `blocked` (`true` first)
3. `lines` descending (total additions + deletions)
4. `updatedAt` ascending (oldest first)
5. `repo.fullName` locale-compare
6. `branch.name` locale-compare

`buildWorkItems` in the same file builds the items and returns `sortWorkItems([...items.values()])`. The UI then partitions them with **`partitionWorkItems`** (also in `src/lib/activity-model.ts`) into `waiting` (`needsYou`) and `inFlight` groups, rendered in `src/components/queue-view.tsx`.

Tests for both behaviors are in **`src/lib/activity-model.test.ts`**, covering `inferAttention`, `sortWorkItems`, and `buildWorkItems`.