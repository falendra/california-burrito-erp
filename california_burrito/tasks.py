# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Scheduled jobs — kept deliberately minimal.

Per docs/DocType_Spec.md section 7, the daily job's only job is flipping
Scheduled/Due -> Overdue. Nothing else. The core PM loop (Program -> Schedule ->
Execution -> next Schedule) must work correctly with this job disabled — it isn't
wired into hooks.py's scheduler_events by default, so the demo doesn't depend on a
background worker firing on schedule. Enable it explicitly (uncomment the
scheduler_events entry in hooks.py) when the due/overdue distinction actually needs
to move on its own.
"""

import frappe
from frappe.utils import today


def mark_overdue_schedules():
	frappe.db.set_value(
		"CB PM Schedule",
		{"due_date": ["<", today()], "status": ["in", ("Scheduled", "Due")]},
		"status",
		"Overdue",
	)
