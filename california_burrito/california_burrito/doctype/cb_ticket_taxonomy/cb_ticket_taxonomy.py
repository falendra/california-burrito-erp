# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CBTicketTaxonomy(Document):
	def before_insert(self):
		# Frappe has no native compound-unique constraint — this is the real
		# logical-uniqueness key: (department, category, sub_category_1, sub_category_2).
		self.taxonomy_key = "|".join(
			[
				self.department or "",
				self.category or "",
				self.sub_category_1 or "",
				self.sub_category_2 or "",
			]
		)

	def before_save(self):
		# Readable label so this doctype's autoname hash never shows up in list views or
		# Link dropdowns (CB Ticket.ticket_taxonomy is hand-picked constantly, unlike the
		# more system-generated PM Schedule/Execution). System-generated, not
		# user-editable — recomputed on every save, unlike taxonomy_key above, since this
		# is a display value that should stay in sync if the parts are ever edited, not a
		# birth-time identity.
		parts = [self.department, self.category, self.sub_category_1, self.sub_category_2]
		self.taxonomy_label = " / ".join(p for p in parts if p)
