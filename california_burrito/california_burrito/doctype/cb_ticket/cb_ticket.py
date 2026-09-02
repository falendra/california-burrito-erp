# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from california_burrito.utils.spare_parts import suggest_spare_part
from california_burrito.utils.technician_assignment import suggest_assigned_technician


class CBTicket(Document):
	def validate(self):
		self._maybe_refresh_suggested_spare_part()
		self._maybe_refresh_assigned_to()

	def _maybe_refresh_suggested_spare_part(self):
		# Recompute only when the ticket is new or its asset/taxonomy actually changed —
		# not on every save, so a manually confirmed/overridden suggestion survives an
		# unrelated edit (e.g. a status change). See docs/DocType_Spec.md section 9.
		if self.is_new():
			relevant_change = True
		else:
			before = self.get_doc_before_save()
			relevant_change = (
				not before or before.asset != self.asset or before.ticket_taxonomy != self.ticket_taxonomy
			)
		if relevant_change:
			self.suggested_spare_part = suggest_spare_part(self.asset, self.ticket_taxonomy)

	def _maybe_refresh_assigned_to(self):
		# Same "relevant change" pattern as suggested_spare_part above, keyed on
		# outlet instead — a manually confirmed/overridden assignment survives an
		# unrelated edit, but refreshes if the outlet changes. See docs/ASSUMPTIONS.md
		# for why this is one deterministic rule, not a routing engine.
		if self.is_new():
			relevant_change = True
		else:
			before = self.get_doc_before_save()
			relevant_change = not before or before.outlet != self.outlet
		if relevant_change:
			self.assigned_to = suggest_assigned_technician(self.outlet)


def on_doctype_update():
	frappe.db.add_index("CB Ticket", ["outlet", "status"])
	frappe.db.add_index("CB Ticket", ["assigned_to", "status"])
