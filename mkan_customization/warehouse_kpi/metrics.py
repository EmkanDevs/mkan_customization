"""Aggregation of normalized activity rows (spec 4.3, 4.7). Used by the page and, later, reports."""
from collections import Counter, defaultdict

import frappe
from frappe.utils import add_days, date_diff, getdate

from mkan_customization.warehouse_kpi.txn_types import (
	ALL_TYPES,
	ISSUED_TYPES,
	MR_CREATED,
	MR_ISSUED,
	ELR_TYPES,
	EQUIPMENT_LOG,
	MR_TYPES,
	OPENING,
	RECEIVED_TYPES,
	TRANSFERRED_TYPES,
)


class Metrics:
	def __init__(self, rows, users):
		users = set(users)
		counted = [r for r in rows if r["type"] != OPENING]
		self.rows = [r for r in rows if r["user"] in users]
		self.work = [r for r in counted if r["docstatus"] == 1 and r["user"] in users]
		self.cancelled = [r for r in counted if r["docstatus"] == 2 and r["user"] in users]
		self.opening = [r for r in self.rows if r["type"] == OPENING and r["docstatus"] == 1]
		self.corrections = [
			r for r in counted if r["docstatus"] == 1 and r["amended_from"] and r["original_owner"] in users
		]
		self.amended = [r for r in self.work if r["amended_from"]]

	def dashboard(self, from_date, to_date):
		type_counts = Counter(r["type"] for r in self.work)
		return {
			"totals": {
				"transactions": len(self.work),
				"lines": sum(r["lines"] for r in self.work),
				"by_type": {t: type_counts.get(t, 0) for t in ALL_TYPES},
				"cancelled": len(self.cancelled),
				"corrections": len(self.corrections),
				"amended": len(self.amended),
				"opening": len(self.opening),
			},
			"chart_types": [[t, n] for t, n in type_counts.most_common()],
			"trend": self.trend(from_date, to_date),
			"quantities": self.quantities(),
			"material_requests": self.material_requests(),
			"equipment": self.equipment(),
		}

	def trend(self, from_date, to_date):
		docs, lines = Counter(), Counter()
		for r in self.work:
			docs[r["date"]] += 1
			lines[r["date"]] += r["lines"]
		days = [str(add_days(from_date, i)) for i in range(date_diff(to_date, from_date) + 1)]
		return {
			"dates": days,
			"transactions": [docs[d] for d in days],
			"lines": [lines[d] for d in days],
		}

	def quantities(self):
		"""Stock-UOM quantities per bucket. UOMs are never added together."""
		buckets = {"received": RECEIVED_TYPES, "issued": ISSUED_TYPES, "transferred": TRANSFERRED_TYPES}
		per_uom = defaultdict(lambda: dict.fromkeys(buckets, 0))
		for r in self.work:
			for bucket, types in buckets.items():
				if r["type"] in types:
					for uom, qty in r["stock_uom_qty"].items():
						per_uom[uom][bucket] += qty
		return [{"uom": uom, **vals} for uom, vals in sorted(per_uom.items())]

	def equipment(self):
		"""Equipment Log split: documents by transaction type, rows by asset or light equipment."""
		logs = [r for r in self.work if r["type"] == EQUIPMENT_LOG]
		by_type = Counter(r["elr_type"] for r in logs)
		return {
			"by_type": [[t, by_type.get(t, 0)] for t in ELR_TYPES],
			"assets": sum(r["assets"] for r in logs),
			"light": sum(r["light"] for r in logs),
		}

	def material_requests(self):
		created = Counter(r["mr_type"] for r in self.work if r["type"] == MR_CREATED)
		issued = Counter(r["mr_type"] for r in self.work if r["type"] == MR_ISSUED)
		extra = sorted((set(created) | set(issued)) - set(MR_TYPES))
		rows = [{"type": t, "created": created[t], "issued": issued[t]} for t in (*MR_TYPES, *extra)]
		return {
			"rows": rows,
			"total": {"created": sum(created.values()), "issued": sum(issued.values())},
		}

	def drill(self, drill):
		"""Rows behind one dashboard number. See spec 6.3 for the drill keys."""
		kind, _, rest = (drill or "all").partition(":")
		if kind == "type":
			return [r for r in self.work if r["type"] == rest]
		if kind == "elr":
			return [r for r in self.work if r["type"] == EQUIPMENT_LOG and r["elr_type"] == rest]
		if kind == "mr":
			return self._mr_rows(rest)
		if kind == "work":
			return self.work
		if kind == "status":
			return self.cancelled
		if kind == "special":
			return {
				"corrections": self.corrections,
				"amended": self.amended,
				"opening": self.opening,
			}.get(rest, [])
		return self.rows

	def _mr_rows(self, rest):
		which, _, mr_type = rest.partition(":")
		wanted = MR_CREATED if which == "Created" else MR_ISSUED
		return [r for r in self.work if r["type"] == wanted and (not mr_type or r["mr_type"] == mr_type)]


def serialize_rows(rows):
	"""Add display values (full names, qty text) for the details table."""
	names = _full_names({r["user"] for r in rows})
	return [_serialize(r, names) for r in rows]


def _serialize(r, names):
	return {
		"name": r["name"],
		"doctype": r["doctype"],
		"date": r["date"],
		"user": r["user"],
		"user_name": names.get(r["user"]) or r["user"],
		"type": _type_label(r),
		"place": _place(r),
		"status": "Cancelled" if r["docstatus"] == 2 else "Submitted",
		"lines": r["lines"],
		"txn_qty": _qty_text(r["txn_uom_qty"]),
		"stock_qty": _qty_text(r["stock_uom_qty"]),
	}


def _type_label(r):
	if r["type"] in (MR_CREATED, MR_ISSUED) and r["mr_type"]:
		return f"{r['type']} ({r['mr_type']})"
	if r["type"] == EQUIPMENT_LOG and r["elr_type"]:
		return f"{r['type']} ({r['elr_type']})"
	return r["type"]


def _place(r):
	if r["locations"] or r["targets"]:
		source, target = ", ".join(r["locations"]), ", ".join(r["targets"])
		return f"{source} → {target}" if target else source
	return ", ".join(r["warehouses"])


def _qty_text(per_uom):
	return ", ".join(f"{_num(q)} {u}" for u, q in per_uom.items())


def _num(value):
	return f"{value:,.2f}".rstrip("0").rstrip(".")


def _full_names(users):
	if not users:
		return {}
	rows = frappe.get_all("User", filters={"name": ["in", list(users)]}, fields=["name", "full_name"])
	return {r.name: (r.full_name or "").strip() for r in rows}
