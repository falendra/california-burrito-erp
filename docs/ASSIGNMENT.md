# Original assignment — verbatim

Two source documents were provided: the email with the actual assignment logistics, and a
candidate brief (from the exercise zip) with scope, data description, and evaluation
criteria. Timeline is **2 days**, self-hosted, own GitHub repo, per the email below.

---

## Email from Harsh Agrawal, CTO in residence, Elevation Capital

> Hi Falendra,
>
> Great speaking with you yesterday. We would like to move you forward to the next round.
> The build exercise, a zip containing the assignment brief and data files, is attached.
>
> Please aim to complete it in about 2 days. Keep us posted on your progress and expected
> completion time.
>
> Here are a few expectations for the exercise:
>
> - Timeline: 2 days, though sooner is better.
> - Deliverables:
>   - A hosted, working solution with login credentials so our team can click through it
>     (feel free to explore free hosting options — a Frappe Cloud trial works well).
>   - The source code, either on a public Git repo or shared as a folder/zip, so we can
>     review it and run the demo.
> - Once we have both, we'll schedule a discussion round to walk through it together.
>
> Feel free to make reasonable assumptions wherever the data or requirements are ambiguous
> and document them within your code or submission. And don't hesitate to reach out if you
> get stuck anywhere.
>
> Looking forward to seeing what you build.
>
> Cheers,
> Harsh Agrawal, CTO in residence, Elevation Capital

---

## Candidate brief (PM_Case_Candidate_Brief.md, from the exercise zip)

**AI tools:** Encouraged — use whatever you'd use on the job. Evaluated on how you *direct
and edit* AI output, not whether you recall Frappe syntax.

### The situation

California Burrito — fast-casual chain, 130+ stores across six Indian cities. Every store
runs a fleet of equipment (ACs, walk-in chillers, fryers, DG sets, fire extinguishers, RO
plants, grease traps, and ~40 other asset types). Two things happen to that equipment:

1. **Planned** — preventive maintenance on a recurring schedule (filters monthly, coils
   quarterly, fire-extinguisher service annually, grease traps weekly).
2. **Unplanned** — things break and someone raises a ticket ("AC not cooling", "chest
   freezer gasket broken").

A team of ~40 maintenance staff, organised by city zonal offices and a reporting chain,
keeps it all running. Today this lives in a pile of spreadsheets. The job: build the Frappe
system that replaces them.

### The data (in the package)

| File | What it is |
|---|---|
| `PM_Case_Before.xlsx` | How preventive maintenance is tracked today. A real, messy export. |
| `PM_Case_Outlets.xlsx` | Store master: 133 outlets, each with a 3-letter code and city. |
| `PM_Case_User_Master.csv` | The maintenance team: role, reporting line, and home zonal office. |
| `PM_Case_Ticket_Buckets.xlsx` | Ticket taxonomy (Dept → Category → Sub-category) and a coded spare-parts catalog. |

These came out of four different systems. Part of the exercise is seeing how they relate.

### The task

Build, in Frappe, the core of this maintenance system. **Not** asked to migrate the files or
reproduce their layout — model the problem properly and ship a working slice.

A reasonable v1 lets us:

1. Define the PM program once — which tasks each kind of asset needs, and how often — and
   **roll it across many stores without re-entering per store**.
2. See what's **due / overdue** and mark it done.
3. Raise a reactive ticket against an asset at a store.
4. Handle the awkward bits in the data gracefully rather than crashing or producing silent
   nonsense.

### Go further (this is where you distinguish yourself)

A v1 that just schedules PM is a pass. Not prescribing any of these — directions past
candidates found worth pursuing. Pick what excites you and what you can ship:

- The planned and unplanned worlds share an equipment taxonomy. Is "PM task" and "ticket"
  really one thing wearing two hats?
- An outlet sits in a city; a city has a zonal office; a zonal office has technicians with a
  reporting chain. What can you do with that path?
- A ticket says "Gasket Broken" on a chest freezer. The spare-parts catalog has a part code
  for exactly that. Can the system help?
- A PM inspection says "check gasket, replace if required" — and it fails. Then what?
- An item goes overdue. Who hears about it, and when?

"We'd rather see one of these built thoughtfully than all of them gestured at."

**Chosen direction for this build:** PM failure → reactive ticket → spare-part suggestion →
technician assignment. Reasoning: it's the one that connects the entire domain model
(Program, Schedule, Execution, Ticket, Spare Part, Technician) in a single vertical slice,
rather than several shallow features.

### Ground rules

- Use Frappe the way it wants to be used. Lean on its primitives.
- Ship something that runs. A small working slice beats a large broken one.
- Cutting scope is expected — just be ready to say **what you cut and why**.
- If the data is ambiguous, make a call, note the assumption, move on. Asking good questions
  is fair game too.

### What to hand over

1. **A live link.** Hosted Frappe site (Frappe Cloud trial is fine) + login credentials.
2. **Code.** Public GitHub repo of the custom app only (not stock Frappe/ERPNext).

### The walkthrough (~15 min after)

Expect questions like: *A new store opens — what do you create? We move AC coil-cleaning to
bi-monthly chain-wide — what do you touch? How many records exist after a year, after five?
How would you route a ticket to the right technician?* No trick answers — they want to see
how you think about the shape of the problem.
