# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from california_burrito.utils.schedule import schedule_new_asset


class CBAsset(Document):
	def before_save(self):
		# Readable label so the AST-##### autoname never leaves a human guessing —
		# same pattern as CB Technician.technician_label and CB Spare Part.part_label.
		# asset_type and outlet are both Links whose own autoname IS their readable
		# name/code, so this is a plain concatenation, no cross-doctype lookup needed.
		# System-generated, not user-editable.
		label = f"{self.asset_type} at {self.outlet}"
		if self.model:
			label += f" ({self.model})"
		self.asset_label = label

	def after_insert(self):
		# Applicability hook: a new Asset automatically becomes eligible for every
		# existing PM Program matching its asset_type — no re-entry per store.
		# See docs/DocType_Spec.md section 7.
		schedule_new_asset(self)
