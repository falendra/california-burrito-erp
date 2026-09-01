# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from california_burrito.utils.recurrence import next_due_date
from california_burrito.utils.schedule import ensure_schedule


# Synthetic taxonomy for tickets auto-raised from a failed PM execution — a deliberate,
# confirmed choice (see PROGRESS.md Phase 3), not a leftover placeholder. The spec's
# on_submit pseudocode pre-fills outlet/asset/source_pm_execution but doesn't say what
# ticket_taxonomy (required on CB Ticket) a system-generated ticket should get, and a
# PM failure isn't the same kind of thing as a hand-raised issue against one of the
# real imported categories (those are built for "AC not cooling"-style reports, not
# "the scheduled filter-clean inspection failed"). Confirmed permanent at Phase 5: check
# whether an equivalent category already exists under the real Maintenance-department
# import data; if nothing fits better, this synthetic row stays rather than forcing PM
# failures into a category meant for something else.
PM_FAILURE_TAXONOMY = {
	"department": "Maintenance",
	"category": "Preventive Maintenance",
	"sub_category_1": "PM Failure",
	"sub_category_2": "",
}


def _get_or_create_pm_failure_taxonomy():
	key = "|".join(
		PM_FAILURE_TAXONOMY[f] for f in ("department", "category", "sub_category_1", "sub_category_2")
	)
	existing = frappe.db.get_value("CB Ticket Taxonomy", {"taxonomy_key": key}, "name")
	if existing:
		return existing
	return frappe.get_doc({"doctype": "CB Ticket Taxonomy", **PM_FAILURE_TAXONOMY}).insert().name


class CBPMExecution(Document):
	def on_update_after_submit(self):
		# Frappe treats a second submit() call on an already-submitted doc as a legitimate
		# "update after submit" transition by default (docstatus 1 -> 1), not an automatic
		# rejection — there is no framework-level double-submit guard to rely on. This
		# doctype has no fields meant to be edited after submission (generated_ticket is set
		# via db_set from inside on_submit, which bypasses this hook entirely), so any update
		# reaching here is a duplicate-submission attempt. This is what satisfies acceptance
		# test 7 ("submit the same PM Execution twice -> second submission rejected").
		frappe.throw(_("CB PM Execution {0} has already been submitted.").format(self.name))

	def on_submit(self):
		# The core recurrence mechanism — no separate scheduling engine needed. All of this
		# runs inside the request's normal DB transaction: any frappe.throw below rolls the
		# whole submit back, so schedule-completion + next-schedule-creation + ticket
		# creation stay atomic. See docs/DocType_Spec.md sections 8-9.
		schedule = frappe.get_doc("CB PM Schedule", self.pm_schedule)

		if schedule.status == "Completed":
			# Guards against a race between two *different* executions targeting the same
			# schedule — distinct from on_update_after_submit above, which guards against
			# resubmitting this *same* execution document.
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

		if self.result == "Failed":
			ticket = frappe.get_doc(
				{
					"doctype": "CB Ticket",
					"outlet": schedule.outlet,
					"asset": schedule.asset,
					"ticket_taxonomy": _get_or_create_pm_failure_taxonomy(),
					"description": _("Auto-raised: PM task {0!r} failed on {1}.").format(
						program.task_description, self.completed_on
					),
					"source_pm_execution": self.name,
				}
			).insert()
			# db_set, not self.generated_ticket = ...; save() — this document is already
			# submitted, and db_set is the standard Frappe way to update a field on a
			# submitted doc from within its own on_submit hook.
			self.db_set("generated_ticket", ticket.name)
