# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CBSparePart(Document):
	def before_save(self):
		# Readable label so this doctype's part_code-only display never leaves a human
		# guessing — part_code alone isn't identifiable, and part_name alone is
		# ambiguous (multiple parts share a name across different equipment models).
		# System-generated, not user-editable. Same pattern as
		# CB Ticket Taxonomy.taxonomy_label.
		self.part_label = f"{self.part_name} — {self.equipment_model} ({self.part_code})"
