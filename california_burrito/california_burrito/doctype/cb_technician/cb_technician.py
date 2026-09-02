# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class CBTechnician(Document):
	def before_save(self):
		# Readable label so this doctype's employee_no-only display never leaves a
		# human guessing — same pattern as CB Ticket Taxonomy.taxonomy_label and
		# CB Spare Part.part_label. System-generated, not user-editable.
		self.technician_label = f"{self.technician_name} ({self.job_title}, {self.zonal_office})"
