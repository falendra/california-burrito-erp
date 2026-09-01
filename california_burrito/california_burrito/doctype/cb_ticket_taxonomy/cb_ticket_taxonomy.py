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
