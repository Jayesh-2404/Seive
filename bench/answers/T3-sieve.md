The app discovers local Git repositories and reads branch status through `src/lib/local-git.ts`, exposed via API routes and consumed by `src/hooks/use-activity.ts` / `src/components/repo-list.tsx`.

## Discovery

Discovery is configured in `src/lib/local-git.ts` with these constants and caches:

- `CONFIG_FILE = ".local-repos.json"` — manual mapping file
- `SCAN_BUDGET_MS = 1_500`, `SCAN_MAX_DIRS = 2_500`, `SCAN_MAX_DEPTH = 3`, `SKIP_DIRS` — filesystem scan limits
- `DISCOVERY_TTL_MS = 30_000` — discovery result cache TTL
- `configCache`, `discoveryCache`, `discoveryPromise` — in-memory caches

Functions involved in discovery/path handling that are visible:

- `src/lib/local-git.ts` — `expandHome`, `uniqueRoots`, `configuredRoots`, `loadConfig`, `isDirectory`
- `src/app/api/local/repos/route.ts` — `PUT` / `DELETE` handlers; `PUT` calls `setLocalMapping` to persist a repo-to-folder mapping
- `src/app/api/github/dashboard/route.ts` — `loadRepository` calls `readLocalState` from `src/lib/local-git.ts` to enrich GitHub repos with local state

## Branch status reading

Git execution and parsing functions in `src/lib/local-git.ts`:

- `runGit` — spawns `git` via `node:child_process` with `GIT_TIMEOUT_MS = 3_000` and `MAX_BUFFER = 2 * 1024 * 1024`
- `parseStatus` — parses `git status` porcelain output into `ParsedStatus` (`branch`, `headSha`, `upstream`, `ahead`, `behind`, `dirty`)
- `parseLog` — parses `git log` to produce `LocalCommit[]`
- `parseRemoteUrl` / `parseGitConfig` / `readOrigin` — read the `origin` remote URL and normalize it to a GitHub `owner/repo` name

The dashboard route returns this as `LocalRead` (`local` / `localError`), and `src/components/repo-list.tsx` renders it via `localAheadLabel`.

## What is missing from the context

The retrieved text for `src/lib/local-git.ts` is truncated after `parseConfig`, so the following are referenced but **not shown**:

- The actual discovery/scanning loop function (the code that walks `configuredRoots` within `SCAN_BUDGET_MS` / `SCAN_MAX_DIRS` / `SCAN_MAX_DEPTH` and respects `SKIP_DIRS`)
- `readLocalState(fullName: string): Promise<LocalRead>` — called by `src/app/api/github/dashboard/route.ts`
- `setLocalMapping(fullName, path)` — called by `src/app/api/local/repos/route.ts`
- Any additional helpers that build the `LocalState` returned to the UI

To fully describe the discovery algorithm, those omitted parts of `src/lib/local-git.ts` would need to be provided.