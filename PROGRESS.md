# Build progress

Update this after every phase. Keep entries short — this is a status log, not a diary.

## Phase 0 — Environment setup
- [ ] frappe_docker cloned
- [ ] Docker Compose services running (db, redis, backend), bind-mounted app directory
- [ ] Site created, bare Frappe (no ERPNext), reachable and login confirmed
- [ ] Confirmed host-side file edits reflect inside the container
- Site URL:
- Status:
- Blockers:

## Phase 1 — Master data
- [ ] App scaffolded, git initialized
- [ ] CB Zonal Office, CB Outlet, CB Asset Type, CB Asset, CB Technician created
- [ ] Manual fixture: 1 outlet, 2 assets, navigable Outlet → Assets
- Status:
- Blockers:

## Phase 2 — PM engine (fixture data only)
- [ ] CB PM Program, CB PM Schedule, CB PM Execution created
- [ ] `ensure_schedule()` implemented in `utils/schedule.py`
- [ ] Test 1 passes (asset applicability — matching asset type only)
- [ ] Test 2 passes (outlet-level applicability — all outlets)
- [ ] Test 4 passes (execution → next schedule)
- [ ] Test 5 passes (late execution doesn't cause drift)
- Status:
- Blockers:

## Phase 3 — Ticket workflow
- [ ] CB Ticket Taxonomy, CB Ticket created
- [ ] Test 6 passes (failed execution → ticket, atomic)
- [ ] Test 7 passes (duplicate submit rejected)
- [ ] Test 8 passes (cross-outlet asset validation)
- Status:
- Blockers:

## Phase 4 — Applicability hooks
- [ ] Test 3 passes (new asset → auto schedule)
- [ ] New outlet → outlet-level programs auto-scheduled
- [ ] Hero scenario manually verified (new outlet + 3 assets → correct partial PM coverage)
- Status:
- Blockers:

## Phase 5 — Import
- [ ] Asset alias normalization table built
- [ ] Frequency resolution (151 recovered / 37 logged unresolved) verified against actual counts
- [ ] Technician fuzzy-match with confidence threshold, unmatched logged
- [ ] All 4 source files imported in dependency order
- [ ] Import summary printed (counts + warnings)
- Status:
- Blockers:

## Phase 6 — Reports
- [ ] Due/overdue PM list view
- [ ] Open tickets by outlet/technician
- Status:

## Phase 7 — Deploy
- [ ] Hosted on Frappe Cloud, demo login created
- [ ] README written (what/why/cut/assumptions/AI usage/how to run)
- [ ] Public GitHub repo pushed (app folder only)
- [ ] Hero scenario clicked through on the live site
- Status:
