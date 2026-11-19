Here is the exact path from GitHub dashboard data to the queue work items, based on the attached context.

### 1. Raw GitHub data is produced by the dashboard API
- **File:** `src/app/api/github/dashboard/route.ts`
- It builds per-repository dashboard payloads containing branches, commits, pull requests, check runs, reviews, and deployments.

### 2. Dashboard data is held as `RepositoryResult[]` in the activity hook
- **File:** `src/hooks/use-activity.ts`
- `useActivity()` manages the selected repositories, refresh interval (`REFRESH_MS`), seen-state in `localStorage`, and the array `activity.results` typed as `RepositoryResult[]`.
- The exact fetch call that invokes the dashboard endpoint is **not shown in the retrieved snippet**, so I can’t name the precise function that performs the HTTP request inside this hook.

### 3. Dashboard repositories are converted into `WorkItem` objects
- **File:** `src/lib/activity-model.ts`
- **`buildWorkItems(results: RepositoryResult[]): WorkItem[]`** is the main conversion function.
  - It iterates over each `RepositoryResult` and extracts `result.repository` of type `DashboardRepository`.
  - It indexes `repo.pullRequests` by branch name.
  - For each `ActivityBranch`, it finds the matching `PullRequest` (if any).
  - It calls **`makeWorkItem(repo, branch, pull)`** to create a `WorkItem`.
  - Attention is classified by **`inferAttention(pull)`** using `pull.draft`, `pull.reviewState`, and `pull.checkState`.
- **`sortWorkItems`** orders the items.
- **`partitionWorkItems(items)`** (used by the view) splits them into `waiting` and `inFlight`.

### 4. The home page derives and summarizes the queue
- **File:** `src/app/page.tsx`
- ```ts
  const workItems = useMemo(() => buildWorkItems(activity.results), [activity.results]);
  const summary = useMemo(() => summarize(workItems), [workItems]);
  ```
- These `workItems` and `summary` are passed into `QueueView`.

### 5. The queue view renders the work items
- **File:** `src/components/queue-view.tsx`
- Receives `items: WorkItem[]` and calls `partitionWorkItems(items)`.
- Renders each item via the **`WorkItem`** component in `src/components/work-item.tsx`.

### Summary of data flow
`src/app/api/github/dashboard/route.ts` → `useActivity()` in `src/hooks/use-activity.ts` → `buildWorkItems()` in `src/lib/activity-model.ts` → `src/app/page.tsx` → `QueueView` in `src/components/queue-view.tsx` → `WorkItem` in `src/components/work-item.tsx`.

### What is missing
The retrieved context does not show the exact fetch call inside `use-activity.ts` that requests `src/app/api/github/dashboard/route.ts`, so I cannot name the function that triggers the network request from the hook.