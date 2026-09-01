# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Fixed-cadence recurrence: next_due_date computes the next occurrence from the
current schedule's due_date, never from the actual completion date — this is what
keeps the cadence fixed instead of drifting when an execution runs late.
"""

import frappe
from frappe.utils import add_days, add_months, add_years, getdate

_FREQUENCY_STEPS = {
	"Weekly": lambda d: add_days(d, 7),
	"Monthly": lambda d: add_months(d, 1),
	"Quarterly": lambda d: add_months(d, 3),
	"6 Monthly": lambda d: add_months(d, 6),
	"Yearly": lambda d: add_years(d, 1),
}


def next_due_date(due_date, frequency):
	"""next_due = due_date + frequency (NOT completed_on + frequency)."""
	step = _FREQUENCY_STEPS.get(frequency)
	if not step:
		frappe.throw(f"Unknown PM Program frequency: {frequency!r}")
	return step(getdate(due_date))
