# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CBPMProgram(Document):
	def before_insert(self):
		# The real logical-uniqueness key is (asset_type, task_description, frequency) —
		# program_name is a human label, not an identity. See docs/DocType_Spec.md section 6.
		self.program_key = f"{self.asset_type or ''}|{self.task_description}|{self.frequency}"
