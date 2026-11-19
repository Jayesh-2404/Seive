Maximum steps for this agent have been reached. Here is the answer based on the attached context.

**Repository picker loading and selection**

- **Component**: `src/components/repo-picker.tsx` — `RepoPicker`
  - Receives `repositories`, `selectedIds`, `onClose`, and `onSave` props. Renders a modal dialog with a search filter and a checkbox list.
  - Local state:
    - `draft`: the working selection, initialized from `selectedIds` filtered to IDs that still exist in `repositories`.
    - `query`: text filter.
  - `filtered` memo:
    - Sorts `repositories` by `fullName`.
    - Filters by `query` against `fullName` and `description`.
  - `toggle(id)` adds or removes an ID from `draft`, respecting `max` (default 12). `atLimit` disables unselected items when the limit is reached.
  - `onSave(draft)` calls the parent's save callback with the draft IDs.

- **Caller / state owner**: `src/app/page.tsx` — `Home`
  - Opens the picker via `openPicker` / `setPickerOpen(true)`.
  - Renders `<RepoPicker open={pickerOpen} repositories={activity.availableRepos} selectedIds={activity.selectedIds} onClose={closePicker} onSave={savePicker} />`.
  - `savePicker` calls `activity.commitSelection(ids)` and closes the picker.

- **Available repositories source**: `src/hooks/use-activity.ts` — `useActivity`
  - Fetches the list of repositories the user can choose from via `loadRepositories`.
  - Calls `GET /api/github/repos` and stores the result in `availableRepos` / `reposRef`.
  - Reads and writes the saved selection IDs from `localStorage` key `agent-activity-repositories-v2` using `readIds()` and `writeIds()`.
  - `commitSelection(ids)` validates IDs against `reposRef.current`, updates `selectedIds`, persists to localStorage, and refreshes the dashboard by calling `fetchDashboard`.

- **API endpoint that loads available repositories**: `src/app/api/github/repos/route.ts` — `GET`
  - Calls GitHub `/user/repos?sort=pushed&per_page=100&affiliation=owner,collaborator,organization_member` through `githubFetch`.
  - Returns a mapped list with `id`, `name`, `fullName`, `description`, `private`, `url`, `defaultBranch`, `pushedAt`, `stars`, `owner`, `avatarUrl`.

- **API endpoint that loads selected repository activity**: `src/app/api/github/dashboard/route.ts` — `GET`
  - Reads `?repo=...` query params, validates up to 12 repository names, and calls `loadRepository` for each.
  - `loadRepository` fetches repository metadata, branches, open pull requests, deployments, reviews, and check runs.

What is **not shown** in the context:
- The CSS module `src/components/repo-picker.module.css`.
- Unit tests for `RepoPicker` or `useActivity`.
- The implementation of `useActivity`’s automatic refresh polling details beyond the 5-minute interval shown.