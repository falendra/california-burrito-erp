# California Burrito Maintenance ERP

Preventive + reactive maintenance system for a 130+ store fast-casual chain, built on Frappe as a take-home exercise for Elevation Capital. Models the domain properly rather than replicating the source spreadsheets: define a PM program once and it rolls across every matching store/asset automatically, executions drive recurrence, and a failed inspection flows through to a ticket with a spare-part suggestion and a technician assignment — the full "go further" chain the brief asked for, not four shallow features.

## Live demo

- **URL**: https://californiaburrito.m.frappe.cloud
- **Login**: `harsh.agrawal@elevationcapital.com`
- **Password**: `harsh@cb2026`
- **Start here**: logging in lands directly on the organized California Burrito workspace — no hunting through Frappe's default desk.

Or jump straight to:

- [Workspace/landing](https://californiaburrito.m.frappe.cloud/desk/cb)
- [Outlets](https://californiaburrito.m.frappe.cloud/desk/cb-outlet)
- [Assets](https://californiaburrito.m.frappe.cloud/desk/cb-asset)
- [PM Programs](https://californiaburrito.m.frappe.cloud/desk/cb-pm-program)
- [PM Schedules](https://californiaburrito.m.frappe.cloud/desk/cb-pm-schedule)
- [Due/Overdue report](https://californiaburrito.m.frappe.cloud/desk/query-report/Due%20and%20Overdue%20PM%20Schedules)
- [Tickets](https://californiaburrito.m.frappe.cloud/desk/cb-ticket)
- [Open Tickets report](https://californiaburrito.m.frappe.cloud/desk/query-report/Open%20Tickets%20by%20Outlet%20and%20Technician)
- [Spare Parts](https://californiaburrito.m.frappe.cloud/desk/cb-spare-part)
- [Technicians](https://californiaburrito.m.frappe.cloud/desk/cb-technician)

## What's built (reasonable v1)

1. **Define a PM program once, roll it across every store** — done. `CB PM Program` (asset type + task + frequency) is a single record; `find_applicable_targets()` computes which outlets/assets it covers *live* from the current `CB Asset`/`CB Outlet` tables, not from whichever outlets happened to be in the import sample. See [`docs/DocType_Spec.md`](docs/DocType_Spec.md#6-cb-pm-program).
2. **See what's due/overdue and mark it done** — done. Native Query Report `Due and Overdue PM Schedules`; marking done means submitting a `CB PM Execution`, which completes the schedule and creates the next occurrence in one atomic step.
3. **Raise a reactive ticket against an asset** — done. `CB Ticket`, either hand-raised or auto-raised from a failed PM execution; see `Open Tickets by Outlet and Technician`.
4. **Handle messy data gracefully** — done. Every ambiguous or unresolvable row (12 PM-frequency groups, 4 technician `reports_to` values, 2 ticket-taxonomy rows) is logged and skipped, never guessed. Full detail in [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md).

## The chosen "go further" direction

**PM failure → reactive ticket → spare-part suggestion → technician assignment.** Chosen because it's the one path that connects the entire domain model — Program, Schedule, Execution, Ticket, Spare Part, Technician — in a single vertical slice, rather than four features that never touch each other.

When a `CB PM Execution` is submitted as **Failed**, a `CB Ticket` is raised automatically, pre-filled with the outlet, asset, and a taxonomy of `Maintenance / Preventive Maintenance / PM Failure`. On save, the ticket auto-suggests a spare part (text match between the asset's model and the spare-parts catalog, narrowed by the ticket's taxonomy) and a technician (first active technician at the outlet's zonal office) — both editable, neither enforced.

Two live examples to click into:
- **`TKT-00001`** — auto-raised from a failed AC filter-clean at the hero-scenario outlet. No spare-part suggestion (the real catalog has no AC parts under that literal name — a real catalog gap, confirmed, not a bug).
- **`TKT-00002`** — hand-raised against a real Chest Freezer with "Gasket Broken," matching ASSIGNMENT.md's own illustrative example exactly: suggests the real `CF01CF` gasket and assigns a real NCR-zone technician.

## Key architectural decisions

- **Program / Schedule / Execution are three doctypes, not one.** Program is the reusable definition; Schedule is one occurrence at one outlet/asset; Execution is the immutable, submittable record of what actually happened. This is what makes "roll out chain-wide" and "audit trail" both work without fighting each other.
- **Execution-driven recurrence, not a calendar generator.** `CB PM Execution.on_submit` is the *only* thing that creates the next Schedule — no rolling-horizon job, no scheduler beyond a single daily status flip.
- **Fixed cadence from `due_date`, never `completed_on`** — a week-late execution doesn't drift the program's cadence forward.
- **`asset` is optional on `Schedule`/`Ticket`** — required when the Program is equipment-level, blank when it's outlet-level (pest control, deep clean). One doctype, two applicability shapes.
- **Applicability is computed live, not from the import sample.** A new store or a new asset becomes eligible for existing programs the moment it's created (`after_insert` hooks), independent of which ~10 outlets happened to appear in the messy PM tracker export.
- **Ticket is not submittable; Execution is.** A ticket's status needs to move backward (reopen); an execution should lock once it's a record of what happened.

Full schema, relationships, and reasoning: [`docs/DocType_Spec.md`](docs/DocType_Spec.md).

## What was deliberately cut, and why

- Separate `Maintenance Task` doctype — collapsed into `PM Program.task_description`.
- Separate `Department`/`Category`/`Subcategory` doctypes — collapsed into one `Ticket Taxonomy` doctype.
- A rolling-horizon schedule generator — unnecessary once recurrence is execution-driven.
- A spare-part *recommendation engine* (scored/ranked/learning) — built a simple text match instead, confirmed or overridden by a person.
- A technician *routing/load-balancing engine* — built one deterministic rule (first active technician at the outlet's zonal office); no load balancing, escalation, or `reports_to`-chain routing.
- Ticket lifecycle enforcement past creation/assignment — no status state-machine, no auto-stamped `resolved_on`, no notifications. The chosen "go further" chain ends at assignment; the brief's v1 list only asks to raise a ticket, not police its lifecycle.
- Microservices, event sourcing, custom RBAC/scheduler/admin UI, dashboards beyond native Frappe views.

Full list with reasoning: [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md#3-scope-deliberately-cut).

## Assumptions on messy data (highlights)

- **12 PM-task groups have no resolvable frequency anywhere** in the source rows — excluded from the PM Program catalog rather than guessed, and logged in the import summary.
- **One technician's zonal office was "Corporate Office," not a city** — a real value in the source file the schema hadn't anticipated; extended the schema rather than drop the person.
- **Technician `reports_to` resolved by fuzzy match** (token containment, then a `difflib` ratio with a 0.75 floor and a 0.1 margin over the runner-up) — 4 of 41 left blank and logged rather than guessed below that bar.
- **111 `CB Asset` rows synthesized**, one per `(outlet, asset type)` pair actually evidenced in the messy PM tracker — the source data is a maintenance log, not an asset register, so this is a documented synthesis, not a real inventory count.

Full list: [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md).

## How AI was used

Claude Code (Sonnet) was the implementation agent for essentially this entire build — every doctype, hook, migration, test, and report was written by it, phase by phase, against a frozen domain spec I wrote and reviewed up front. My role was architecture and domain decisions (the doctype boundaries, what gets cut, how ambiguous data gets resolved), plus reviewing every phase's diff and test output before moving to the next one — nothing merged on "looks right."

That review process caught real bugs, not just style nits:

- **A double-submit gap.** I'd assumed (and initially documented) that Frappe rejects re-submitting an already-submitted document by default. It doesn't — it treats a second `submit()` as a legitimate `on_update_after_submit` transition. A test failure surfaced this; the fix was an explicit guard, not a framework feature I could rely on.
- **A test that passed by coincidence, not by correctness.** Two tests computed a schedule date two different ways — `today()` and a hardcoded literal — that happened to be equal for the entire project so far. When the dev clock advanced a day, one test caught a real duplicate-schedule bug the other test's assertions were too loose to notice. Fixed the test, then audited every other test file for the same pattern.
- **A report showing raw internal IDs instead of names**, despite the underlying doctypes having the display-label configuration set correctly. Turned out that configuration only affects Link *form fields* — a Query Report's SQL returns exactly what its query selects, with no automatic title resolution. Confirmed by reading Frappe's own rendering code, then fixed by joining the target table in the SQL directly.

Nothing here was "trust the AI and move on" — every claim in `PROGRESS.md` (record counts, test results, a bug's root cause) was verified against the actual running site or test output before being accepted, not just asserted by the agent.

## Running it locally

```bash
bench get-app <this-repo-url> --branch version-16
bench install-app california_burrito
bench execute california_burrito.utils.import_data.run
bench execute california_burrito.utils.seed_demo.run
```

Both scripts take no arguments — `import_data.run()` resolves `data/source/` relative to the installed app (via `frappe.get_app_path()`), so the same call works unchanged in any environment. Both are also exposed as REST endpoints (`/api/method/california_burrito.utils.import_data.run`, `...seed_demo.run`) for environments without SSH/console access. Full environment setup (Docker, bind mounts, site creation) is in `PROGRESS.md`'s Phase 0 section; process/conventions are in `CLAUDE.md`.

## Tests

```bash
bench --site <site> run-tests --app california_burrito
```

19 tests, covering all 8 numbered acceptance scenarios from `docs/DocType_Spec.md` plus the full hero-scenario walkthrough, spare-part suggestion, and technician assignment.
