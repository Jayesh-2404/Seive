Maximum steps for this agent have been reached. I can still answer the question using the provided context.

## How the UI splits the queue and renders each work item

**Splitting the queue:**

- **`src/components/queue-view.tsx`**, function `QueueView`, splits the items with:
  ```ts
  const { waiting, inFlight } = partitionWorkItems(items);
  ```
- **`src/lib/activity-model.ts`**, function `partitionWorkItems`, performs the actual split (exact logic is not shown in the retrieved snippets, but its return type is `{ waiting: WorkItem[]; inFlight: WorkItem[] }`).

**Producing the items passed to the queue:**

- **`src/app/page.tsx`**, function `Home`, builds the list with:
  ```ts
  const workItems = useMemo(() => buildWorkItems(activity.results), [activity.results]);
  ```
- **`src/lib/activity-model.ts`**, function `buildWorkItems`, creates `WorkItem` objects per branch/pull request.

**Rendering each work item:**

- **`src/components/work-item.tsx`**, function `WorkItem`, renders a single `WorkItem`.
- It derives tone, status, title, link, lines/files, check count, etc., and returns an `<li className={styles.item} data-tone={tone}>`.
- Helper **`checksLabel`** inside `src/components/work-item.tsx` formats the check-state label.

**Summary flow:** `Home` → `buildWorkItems` → passed as `items` to `QueueView` → `partitionWorkItems` → rendered as `WorkItem` components.

What is missing: the full body of `partitionWorkItems` in `src/lib/activity-model.ts` (only its call signature and return shape are visible), and the JSX after the truncation point in `QueueView` and `WorkItem`.