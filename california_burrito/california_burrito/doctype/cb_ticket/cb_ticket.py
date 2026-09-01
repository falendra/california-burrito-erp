# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from california_burrito.utils.spare_parts import suggest_spare_part


class CBTicket(Document):
	def validate(self):
		self._maybe_refresh_suggested_spare_part()

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


def on_doctype_update():
	frappe.db.add_index("CB Ticket", ["outlet", "status"])
	frappe.db.add_index("CB Ticket", ["assigned_to", "status"])
