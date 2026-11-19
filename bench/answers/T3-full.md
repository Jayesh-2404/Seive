Maximum steps for this agent have been reached. No files have been modified; the user asked a factual question about how the app discovers local Git repositories and reads their branch status, and I can answer that directly from the supplied context.

**How local repositories are discovered**

Local repository discovery and branch status are handled in `src/lib/local-git.ts`.

- `readLocalState(fullName, defaultBranch)` is the main entry point used by the dashboard API (`src/app/api/github/dashboard/route.ts`) to load local state for a repository.
- `readLocalState` calls `readLocalStateUncapped`, which first resolves the local path via `resolveLocalPath(fullName)`.
- `resolveLocalPath` checks two sources:
  1. Explicit mappings in `.local-repos.json` loaded by `loadConfig()` / `parseConfig(raw)`.
  2. Automatic discovery from a set of roots: configured roots, the `LOCAL_REPO_ROOTS` env variable, and hard-coded defaults such as `~/projects`, `~/code`, `~/dev`, `~/repos`, `~/git`, `~/source/repos`, `~/Documents/GitHub`, plus the parent of the current working directory.
- `discoverLocalRepositories(roots, force)` orchestrates the scan, with a 30-second cache (`DISCOVERY_TTL_MS`).
- `scanRoots(roots)` performs a breadth-first scan up to depth `SCAN_MAX_DEPTH = 3`, `SCAN_MAX_DIRS = 2,500`, and `SCAN_BUDGET_MS = 1,500` milliseconds, skipping common build/cache directories (`node_modules`, `.next`, `dist`, etc.).
- For each directory containing a `.git` folder, `readOrigin(root)` reads the Git config and `parseRemoteUrl` / `parseGitConfig` extracts the GitHub `owner/repo` key.

**How branch status is read**

Once a local path is resolved:

- `runGit(cwd, args)` executes `git` with a 3-second timeout.
- `readLocalStateUncapped` calls `git rev-parse --show-toplevel` to confirm the repo root.
- It then runs `git status --porcelain=v2 --branch --untracked-files=normal` and parses the output with `parseStatus(stdout)`, which extracts:
  - current branch / detached HEAD
  - HEAD SHA
  - upstream name
  - ahead/behind counts
  - changed and untracked file counts
- `readLocalBranches(root, defaultBranch, currentBranch, hasUncommittedChanges)` then:
  - Resolves the default branch SHA from `refs/heads/<default>` or `refs/remotes/origin/<default>`.
  - Lists local refs with `git for-each-ref --sort=-committerdate` (limit `LOCAL_BRANCH_LIMIT = 25`).
  - For each branch, computes ahead/behind via `git rev-list --left-right --count <base>...<branch>`.
  - Reads the newest commits ahead of base with `git log` (limit `BRANCH_COMMIT_LIMIT = 8`), parsed by `parseLog`.
- Unpushed commits on the current branch are read separately with `git log @{u}..HEAD` (or `git log HEAD --not --remotes` if no upstream), limited to `UNPUSHED_LIMIT = 20`.

**Files and functions involved**

- `src/lib/local-git.ts`: `readLocalState`, `readLocalStateUncapped`, `resolveLocalPath`, `discoverLocalRepositories`, `scanRoots`, `readOrigin`, `parseConfig`, `parseStatus`, `parseLog`, `parseRemoteUrl`, `parseGitConfig`, `readLocalBranches`, `runGit`, `setLocalMapping`
- `src/app/api/github/dashboard/route.ts`: calls `readLocalState(name, repository.defaultBranch)` while building dashboard results
- `src/app/api/local/repos/route.ts`: `PUT`/`DELETE` handlers that call `setLocalMapping` to link/unlink a local clone
- `src/components/repo-history.tsx`: displays local branch/unpushed data and the “Link a folder” UI

**What is missing from the context**

- The actual `.local-repos.json` schema is described but the file itself is not present in the context (only inferred from `parseConfig` and the tests).
- No client-side code for triggering discovery; discovery happens server-side when the dashboard API refreshes.