# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CBPMProgram(Document):
	def before_insert(self):
		# The real logical-uniqueness key is (asset_type, task_description, frequency) —
		# program_name is a human label, not an identity. See docs/DocType_Spec.md section 6.
		self.program_key = f"{self.asset_type or ''}|{self.task_description}|{self.frequency}"

	def before_save(self):
		# Recomputed on every save, not just set once at creation, so program_name
		# always reflects the record's current fields (e.g. after a frequency change)
		# instead of going stale. Any program_name passed in at creation (import_data.py,
		# seed_demo.py) is intentionally overwritten by this — it's a derived display
		# label, not user-authored free text. "Outlet-level" fallback matches
		# program_key's own '' fallback for a blank asset_type.
		self.program_name = f"{self.asset_type or 'Outlet-level'} - {self.task_description} - {self.frequency}"
