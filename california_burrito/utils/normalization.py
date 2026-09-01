# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Deterministic normalization for the Phase 5 import — no AI-invented values. Every
mapping table here was hand-built by inspecting data/source/PM_Case_Before.xlsx and
data/source/PM_Case_Ticket_Buckets.xlsx directly; see PROGRESS.md Phase 5 for the full
derivation and the exact counts each one produces against the real files.
"""

import difflib
import re


def normalize_whitespace(value):
	return re.sub(r"\s+", " ", (value or "").strip())


# Canonical Asset Type per docs/DocType_Spec.md section 4 — hand-built from the alias
# clusters in PM_Case_Before.xlsx's "Asset" column (20 distinct raw values, including
# blank, collapse to 12 canonical types + the blank/outlet-level case).
ASSET_TYPE_ALIASES = {
	"AC": "Air Conditioner",
	"A/C Plant": "Air Conditioner",
	"Aircon Unit": "Air Conditioner",
	"Air Conditioner / AC Plant / FCU / AHU": "Air Conditioner",
	"WIC": "Walk-in Chiller",
	"Walk-IN Chiller": "Walk-in Chiller",
	"Walk in Chiller": "Walk-in Chiller",
	"Fire Ext.": "Fire Extinguisher",
	"Fire Extingushers": "Fire Extinguisher",
	"Fire Extinguisher": "Fire Extinguisher",
	"DG Set & AMF Panel": "DG Set & AMF Panel",
	"RO Plant": "RO Plant",
	"Kitchen Exhaust Fan": "Kitchen Exhaust Fan",
	"Hot Line/Warmer": "Hot Line/Warmer",
	"Fryers": "Fryer",
	"Tortila Press": "Tortilla Press",  # source typo, fixed
	"Drain Lines / Grease Trap": "Drain Lines / Grease Trap",
	"Chest Freezer": "Chest Freezer",
	"Ice Cube Machine": "Ice Cube Machine",
}


def canonicalize_asset_type(raw_asset):
	"""Return the canonical Asset Type name for a raw Before.xlsx 'Asset' value, or
	None for a blank value (an outlet-level row — pest control, deep clean).

	Raises on a genuinely unmapped value rather than guessing — every value actually
	present in the source file is covered above; a new, unmapped value showing up
	means the source changed and this table needs a human to extend it, not a silent
	best-effort default.
	"""
	value = normalize_whitespace(raw_asset)
	if not value:
		return None
	if value not in ASSET_TYPE_ALIASES:
		raise ValueError(f"Unmapped asset value in Before.xlsx: {raw_asset!r}")
	return ASSET_TYPE_ALIASES[value]


# Before.xlsx's "Freq" strings don't all match CB PM Program.frequency's Select options
# verbatim.
FREQUENCY_ALIASES = {
	"Weekly": "Weekly",
	"Monthly": "Monthly",
	"Qtrly": "Quarterly",
	"6 month": "6 Monthly",
	"Yearly": "Yearly",
}


def normalize_frequency(raw_freq):
	"""Return the canonical frequency Select-option string, or None for blank."""
	value = normalize_whitespace(raw_freq)
	if not value:
		return None
	if value not in FREQUENCY_ALIASES:
		raise ValueError(f"Unmapped frequency value in Before.xlsx: {raw_freq!r}")
	return FREQUENCY_ALIASES[value]


def parse_spare_part(sub_category_1):
	"""Split a 'Sub Category 1' string like '2DC01CF Gasket' into (part_code, part_name)
	— the part code is the first whitespace-delimited token, the name is the rest.
	Returns None if the text doesn't split into exactly a code plus a name.
	"""
	value = normalize_whitespace(sub_category_1)
	parts = value.split(" ", 1)
	if len(parts) != 2 or not parts[0] or not parts[1]:
		return None
	return parts[0], parts[1]


def match_reports_to(raw_value, candidate_names, confidence=0.75, margin=0.1):
	"""Fuzzy-match a 'Reports to' name against real technician names.

	Three passes, cheapest/most certain first:
	1. Exact match after whitespace normalization (handles e.g. 'Azad  Khan ' -> 'Azad Khan').
	2. Token containment: every word of raw_value appears among a candidate's words
	   (handles e.g. 'Sujith H S' -> 'Sujith Kumar H S'). Accepted only if exactly one
	   candidate qualifies — more than one is treated as ambiguous, not a match.
	3. A difflib similarity ratio, accepted only if it clears both an absolute
	   `confidence` floor and a `margin` over the runner-up — a close call between two
	   plausible candidates is not a confident match either.

	Returns (matched_name, method_description) on success, or (None, reason) when
	nothing clears the bar — this is deliberate: below-threshold candidates are never
	auto-persisted, only logged for manual confirmation.
	"""
	target = normalize_whitespace(raw_value)
	if not target:
		return None, "blank"
	if target in candidate_names:
		return target, "exact"

	target_tokens = set(target.split())
	containment = [n for n in candidate_names if target_tokens.issubset(set(n.split()))]
	if len(containment) == 1:
		return containment[0], f"token-containment:{containment[0]}"
	if len(containment) > 1:
		return None, f"ambiguous token-containment candidates: {containment}"

	scored = sorted(
		((difflib.SequenceMatcher(None, target.lower(), n.lower()).ratio(), n) for n in candidate_names),
		reverse=True,
	)
	if not scored:
		return None, "no candidates"
	top_score, top_name = scored[0]
	runner_up_score = scored[1][0] if len(scored) > 1 else 0.0
	if top_score >= confidence and (top_score - runner_up_score) >= margin:
		return top_name, f"difflib:{top_name}:{top_score:.2f}"
	return None, f"unresolved — best candidate {top_name!r} scored {top_score:.2f} (below threshold)"
