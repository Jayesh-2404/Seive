## Pull request attention states

Computed in **`src/lib/activity-model.ts`** by the exported function **`inferAttention(pull: PullRequest | null): AttentionState`** (lines 24–34 in the retrieved chunk):

```ts
export function inferAttention(pull: PullRequest | null): AttentionState {
  if (!pull) return "no-pull-request";
  if (pull.draft || pull.reviewState === "draft") return "draft";
  if (pull.checkState === "failure") return "checks-failing";
  if (pull.reviewState === "changes_requested") return "agent-revising";
  if (pull.reviewState === "approved") return "approved";
  if (pull.reviewState === "in_review") return "in-review";
  if (pull.reviewState === "ready") return "your-review";
  return "unknown";
}
```

The order matters: draft and check failures are evaluated before review states. The resulting `AttentionState` type is defined in **`src/lib/activity-types.ts`** (`AttentionState` at line 191). UI labels and color tones for these states are provided by **`src/lib/format.ts`**: `statusLabel(state)` and `statusTone(state)`.

The attention state is consumed by **`makeWorkItem`** in the same model file (`src/lib/activity-model.ts`, lines 35–58), which also derives:

- `needsYou`: `true` when attention is `"your-review"` or `"approved"`
- `blocked`: `true` when `pull.checkState === "failure"`

## Work item sorting

Sorting is performed by **`sortWorkItems`** in **`src/lib/activity-model.ts`** (declared at line 102), but **the body of `sortWorkItems` is not included in the attached context**, so the exact sort keys and direction are missing.

What the context does show:

- `sortWorkItems` is called downstream (implied by the symbol list), and the items are later partitioned by **`partitionWorkItems`** in the same file (`src/lib/activity-model.ts`, line 115).
- `partitionWorkItems` is called by **`QueueView`** in **`src/components/queue-view.tsx`** (line 26), producing `{ waiting, inFlight }`, which are rendered as separate groups.

So the full flow is: `buildWorkItems` → `sortWorkItems` → `partitionWorkItems` → rendered by `QueueView`. The sorting criteria itself are not visible in the provided snippets.