# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from california_burrito.utils.recurrence import next_due_date
from california_burrito.utils.schedule import ensure_schedule


class CBPMExecution(Document):
	def on_submit(self):
		# The core recurrence mechanism — no separate scheduling engine needed. All of this
		# runs inside the request's normal DB transaction: any frappe.throw below rolls the
		# whole submit back, so schedule-completion + next-schedule-creation stay atomic.
		# See docs/DocType_Spec.md section 8.
		schedule = frappe.get_doc("CB PM Schedule", self.pm_schedule)

		if schedule.status == "Completed":
			# Guards against a race between two executions targeting the same schedule —
			# distinct from Frappe's own single-submission guard on this document itself.
			frappe.throw(
				_("PM Schedule {0} has already been completed by another execution.").format(schedule.name)
			)

		schedule.status = "Completed"
		schedule.save()

		program = frappe.get_doc("CB PM Program", schedule.pm_program)
		next_due = next_due_date(schedule.due_date, program.frequency)
		# Regardless of Passed/Failed/Skipped — a failed inspection doesn't kill the
		# recurring program.
		ensure_schedule(schedule.pm_program, schedule.outlet, schedule.asset, next_due)

		# Failed -> CB Ticket creation is added in Phase 3 (CB Ticket doesn't exist yet as
		# of Phase 2 — see PROGRESS.md).
