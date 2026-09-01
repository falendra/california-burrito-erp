# CLAUDE.md — California Burrito Maintenance ERP

## What this is
A Frappe custom app implementing preventive + reactive maintenance for California Burrito
(130+ store fast-casual chain). This is a take-home build exercise under a hard time budget —
optimize for a small, correct, demoable slice over comprehensive coverage. A working narrow
system beats a broken broad one.

## Priority of information
1. `docs/ASSIGNMENT.md` — the original brief. This is WHAT was actually asked for and how
   it's evaluated. If an implementation choice seems to conflict with it, the brief wins.
2. `docs/DocType_Spec.md` — the frozen domain contract, derived from the brief. READ-ONLY
   during implementation. Do not modify it. If you believe it genuinely contradicts the
   brief, stop and ask — do not silently resolve the conflict either direction.
3. This file (`CLAUDE.md`) — HOW to work: process, conventions, communication. Also
   READ-ONLY during implementation unless I explicitly ask you to update it.
4. Existing code and tests.
5. Your own implementation judgment — lowest priority, used only for details none of the
   above cover (variable names, file layout within `utils/`, etc.).

## Source of truth for domain decisions
`docs/DocType_Spec.md` reflects several rounds of deliberate review — treat it as reviewed and
final, not a first draft. **Do not introduce new DocTypes, rename relationships, change
applicability rules, or add abstraction layers without stopping and asking me first.**

## Source data
Raw files in `data/source/`:
- `PM_Case_Before.xlsx` — messy real PM tracker export. Used ONLY to derive PM Program
  definitions (asset type + task + frequency). Never used to decide which outlets/assets
  receive PM — that's computed fresh from `CB Asset` / `CB Outlet` at generation time via
  `find_applicable_targets()`, so it covers all outlets, not just the ~10 in this sample.
- `PM_Case_Outlets.xlsx` — 133 outlets, clean, direct import.
- `PM_Case_User_Master.csv` — 41 technicians. `Reports to` values don't exact-match `Name`
  values — requires fuzzy matching with a confidence threshold; below threshold, leave blank
  and log it, don't guess.
- `PM_Case_Ticket_Buckets.xlsx` — 844 rows mixing ticket taxonomy (`Department = Maintenance`)
  and spare parts catalog (`Department = Spare Parts`, part code embedded in the
  `Sub Category 1` text).

## Build order — do not skip ahead
Follow the phases in `docs/DocType_Spec.md`'s build sequence exactly, starting with Phase 0:

### Phase 0 — Environment setup (fully agent-driven, no manual steps expected)
You own this end to end using your bash tool. Do not ask the user to run commands, open
VS Code, or click through any UI — script it yourself.
1. Clone `https://github.com/frappe/frappe_docker` into the project.
2. Bring up a local bench with Docker Compose, with the app source directory **bind-mounted
   to the host filesystem** (not container-only) so your normal file-editing tools work
   directly on the code without going through `docker exec` for every edit. Model this on
   `frappe_docker`'s `devcontainer-example` compose configuration, invoked directly via
   `docker compose` rather than through VS Code's UI.
3. Bring up services (db, redis, backend), create a site (e.g. `development.localhost`), do
   **not** install ERPNext — bare Frappe only, since this is a from-scratch custom app.
4. Verify: confirm the site responds (e.g. `curl` the local port, or `bench doctor` /
   `bench --site <site> list-apps` via `docker exec`), and confirm you can create and edit a
   test file in the bind-mounted app directory from the host side.
5. Only if genuinely blocked (e.g. Docker daemon not running, port conflict with no safe
   resolution) — stop and tell the user exactly what manual action is needed, in one
   sentence, rather than guessing around it silently.
6. Update `PROGRESS.md`, report the site URL and login, and stop for confirmation before
   Phase 1.

### Phase 1 onward
1. Scaffold app + 5 master DocTypes (Zonal Office, Outlet, Asset Type, Asset, Technician).
2. Fixture data only (1 outlet, 2 assets, 1 PM Program, by hand) — prove
   Program → Schedule → Execution → next Schedule, including idempotent generation and
   fixed-cadence recurrence (`due_date + frequency`, never `completed_at + frequency`).
3. Failed execution → Ticket, atomically, with duplicate-submit rejection.
4. New Asset / new Outlet → automatic schedule generation via applicability hooks.
5. Import script + deterministic normalization, run against real data.
6. Minimal due/overdue + ticket views using native Frappe list/report views — no custom
   dashboard code unless everything above is solid and there's time left.
7. README + deploy.

**After each phase, run the relevant acceptance tests from `docs/DocType_Spec.md`, update
`PROGRESS.md`, and stop for my review before continuing to the next phase.** Do not proceed to
import (phase 5) until phases 1–4 pass on fixture data — mixing untested business logic with
real messy data at the same time is the failure mode we're specifically avoiding.

## Hard rules
- Business logic lives in `california_burrito/utils/` (`schedule.py`, `recurrence.py`,
  `normalization.py`). DocType controllers and hooks call into these, not the other way around.
- `ensure_schedule()` is the ONLY function that creates a `CB PM Schedule` document. It is
  called from exactly four places (initial seeding, `Asset.after_insert`,
  `Outlet.after_insert`, `PM Execution.on_submit`) — never duplicate its logic inline anywhere.
- Frappe has no native compound unique constraint. `generation_key` (on PM Schedule) and
  `program_key` (on PM Program) must be single computed `Data` fields with `"unique": 1`,
  populated in `before_insert`, wrapped in `try/except frappe.UniqueValidationError` on insert
  (not just a pre-check `exists()` call — that has a race condition).
- Never invent business data. If a frequency, asset-type mapping, or technician match is
  ambiguous or missing, skip it and log it in the import summary — do not guess a default.
- Do not build: microservices, any scheduler beyond the single daily job that flips
  Scheduled/Due → Overdue, a spare-part recommendation engine, a separate Maintenance Task
  doctype, separate Department/Category/Subcategory doctypes (use one `CB Ticket Taxonomy`),
  or dashboards beyond native Frappe list/report views.
- Ticket is NOT a submittable doctype (status needs to move backward/reopen). PM Execution IS
  submittable (locks the record, gives a clean `on_submit` hook).

## Testing
Implement and run the 8 acceptance tests plus the hero demo scenario from
`docs/DocType_Spec.md` as real Frappe tests (`bench run-tests`). A phase is done when its
tests pass, not when the code merely runs without error.

## Commits
Small, one logical change per commit (scaffold app → master doctypes → PM engine →
recurrence → ticket workflow → applicability hooks → import → reports → deploy). Never commit
`__MACOSX/` or `.DS_Store` files from the source data zip.

## When you're unsure
Stop and ask rather than picking a reasonable-sounding default — this repo already has a
documented answer for most ambiguous cases in `docs/DocType_Spec.md`. If it's genuinely not
covered there, flag it explicitly rather than silently deciding.

## Never fabricate business data
`Before.xlsx` is not a real asset register — the demo needs actual `CB Asset` rows to exist
before applicability logic means anything, and the spec allows synthesizing a representative
set. **Do not silently generate production-looking numbers** (e.g. deciding on your own that
every outlet gets "4 ACs, 2 freezers, 3 fryers"). If you need fixture/demo assets to make the
system demoable, generate a small, clearly-labeled set and tell me exactly what you assumed
and why — this becomes a documented assumption in the README, not a hidden implementation
detail. The same rule applies to any other gap in the source data: log it, don't invent it.

## Assumptions log
`docs/ASSUMPTIONS.md` is the compiled, reviewable record of every assumption and
ambiguity call — organized by category (data ambiguity, domain modeling choices, cut
scope, synthesized data), not chronologically. It's what `README.md`'s assumptions
section points to. From Phase 6 onward: **any new assumption or ambiguity call gets
added to `docs/ASSUMPTIONS.md` directly, not just narrated in `PROGRESS.md`.**
`PROGRESS.md` stays the detailed phase-by-phase record of how each was found and
verified; `docs/ASSUMPTIONS.md` stays the short, one-or-two-sentence summary of the
ambiguity, the decision, and why.

## AI development discipline
Use yourself aggressively for implementation, but preserve human ownership of architecture
and business decisions.

Before a non-trivial implementation change:
1. Check the relevant section of `docs/DocType_Spec.md`.
2. Prefer existing Frappe conventions over inventing new abstractions.
3. Make the smallest change that satisfies the requirement.
4. Run the relevant tests after the change.
5. Do not "fix" the specification by changing the domain model to make implementation easier.
6. If implementation reveals a genuine contradiction in the spec, stop and ask — don't
   silently resolve it.

Don't generate large amounts of code speculatively. Build one vertical slice at a time.

## Working style
At the start of each phase: state the exact goal, which files/doctypes will change, and
which acceptance tests will prove the phase is done.

During implementation: implement, test, fix. Don't stop for confirmation on routine details
(field ordering, naming series format, etc.) — use judgment there.

At the end of each phase:
- Run the relevant acceptance tests and report pass/fail for each.
- Update `PROGRESS.md`.
- Summarize files changed.
- Report any assumptions made or blockers hit.
- **Stop and wait for my go-ahead before starting the next phase.**
