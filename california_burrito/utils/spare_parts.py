# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Spare-part suggestion for CB Ticket. Per docs/DocType_Spec.md section 9: match
CB Spare Part.equipment_model against the ticket's Asset.model (or Asset.asset_type
if model is blank), narrowed by the ticket's taxonomy category/sub-category text
where that helps. Simple text match, not a recommendation engine — the user
confirms or overrides the suggestion.
"""

import re

import frappe


def _keywords(text):
	"""Lowercase, non-trivial (2+ char) words from free text — deliberately simple,
	not real NLP."""
	return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 1]


def suggest_spare_part(asset_name, ticket_taxonomy_name):
	"""Return a CB Spare Part name to suggest, or None if nothing matches or there's
	nothing to match against (no asset, or the asset has no model/asset_type)."""
	if not asset_name:
		return None

	asset = frappe.db.get_value("CB Asset", asset_name, ["model", "asset_type"], as_dict=True)
	if not asset:
		return None
	descriptor = asset.model or asset.asset_type
	if not descriptor:
		return None

	candidates = frappe.get_all(
		"CB Spare Part",
		filters={"equipment_model": ["like", f"%{descriptor}%"], "active": 1},
		fields=["name", "part_name"],
	)
	if not candidates:
		return None
	if len(candidates) == 1:
		return candidates[0].name

	# Multiple parts fit the equipment — narrow using the ticket's taxonomy text.
	if ticket_taxonomy_name:
		taxonomy = frappe.db.get_value(
			"CB Ticket Taxonomy",
			ticket_taxonomy_name,
			["category", "sub_category_1", "sub_category_2"],
			as_dict=True,
		)
		if taxonomy:
			taxonomy_words = set(
				_keywords(taxonomy.category)
				+ _keywords(taxonomy.sub_category_1)
				+ _keywords(taxonomy.sub_category_2)
			)
			narrowed = [c for c in candidates if taxonomy_words & set(_keywords(c.part_name))]
			if narrowed:
				candidates = narrowed

	# Still more than one plausible candidate (or no taxonomy to narrow with) — pick
	# deterministically rather than guess a "best" one; this is a simple text match,
	# not a recommendation engine, and the user confirms or overrides regardless.
	return sorted(candidates, key=lambda c: c.name)[0].name
