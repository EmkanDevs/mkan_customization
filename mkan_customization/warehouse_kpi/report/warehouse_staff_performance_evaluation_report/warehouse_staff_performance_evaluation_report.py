"""Script Report: Warehouse Staff Performance Evaluation Report (spec 6.4).

One row per storekeeper. Scope and source rows come from the shared scope.resolve and
load_activity, so permissions and numbers match the dashboard. Counting is done here.
"""
from collections import defaultdict

import frappe

from mkan_customization.warehouse_kpi import scope
from mkan_customization.warehouse_kpi.sources import load_activity
from mkan_customization.warehouse_kpi.txn_types import EQUIPMENT_LOG, MR_CREATED, MR_ISSUED, OPENING

# fieldname, label, transaction type counted in the column
TYPE_COLUMNS = [
	("purchase_receipts", "Purchase Receipts", "Purchase Receipt"),
	("material_returns", "Material Returns", "Material Return"),
	("return_requests", "Return Requests", "Return Request"),
	("petty_cash", "Petty Cash", "Petty Cash Receipt"),
	("other_receipts", "Other Receipts", "Other Material Receipt"),
	("material_issues", "Material Issues", "Material Issue"),
	("supplier_returns", "Supplier Returns", "Supplier Return"),
	("transfers", "Transfers", "Stock Transfer"),
	("stock_adjustments", "Stock Adjustments", "Stock Adjustment"),
	("mr_created", "MR Created", MR_CREATED),
	("mr_issued", "MR Issued", MR_ISSUED),
	("equipment_logs", "Equipment Logs", EQUIPMENT_LOG),
]
# Counted per Equipment Log row, so they can exceed the number of documents.
ROW_COLUMNS = [("assets", "Assets", "assets"), ("light_equipment", "Light Equipment", "light")]
TAIL_COLUMNS = [("cancelled", "Cancelled"), ("corrections", "Corrections"), ("amended", "Amended By User")]


def execute(filters=None):
	report = PerformanceReport(filters)
	return report.columns(), report.data()


class PerformanceReport:
	def __init__(self, filters):
		self.ctx = scope.resolve(filters)
		self.f = self.ctx["filters"]
		self.query, rows = load_activity(self.ctx)
		self.users = sorted(self.query.users)
		self._split(rows)

	def columns(self):
		cols = [
			{"fieldname": "storekeeper_name", "label": "Stock User", "fieldtype": "Data", "width": 180},
			{"fieldname": "user", "label": "User", "fieldtype": "Data", "hidden": 1},
			{"fieldname": "warehouses", "label": "Warehouses / Locations", "fieldtype": "Data", "width": 200},
			self._int("transactions", "Transactions"),
			self._int("lines", "Item Lines"),
		]
		cols += [self._int(key, label) for key, label, _t in TYPE_COLUMNS]
		cols += [self._int(key, label) for key, label, _f in ROW_COLUMNS]
		cols += [self._int(key, label) for key, label in TAIL_COLUMNS]
		cols.append(
			{"fieldname": "latest_score", "label": "Latest Evaluation Score", "fieldtype": "Float", "precision": 2, "width": 140}
		)
		return cols

	def data(self):
		names = _full_names(self.users)
		scores = self._latest_scores()
		rows = [self._row(user, names, scores) for user in self.users]
		rows.sort(key=lambda r: (r["storekeeper_name"] or "").lower())  # no ranking by score
		return rows

	def _split(self, rows):
		"""Group rows the same way the dashboard counts them."""
		users = set(self.users)
		counted = [r for r in rows if r["type"] != OPENING]
		self.work = _group([r for r in counted if r["docstatus"] == 1 and r["user"] in users], "user")
		self.cancelled = _group([r for r in counted if r["docstatus"] == 2 and r["user"] in users], "user")
		self.amended = _group(
			[r for r in counted if r["docstatus"] == 1 and r["amended_from"] and r["user"] in users], "user"
		)
		# A correction is credited to the owner of the document that was amended.
		self.corrections = _group(
			[r for r in counted if r["docstatus"] == 1 and r["amended_from"] and r["original_owner"] in users],
			"original_owner",
		)

	def _row(self, user, names, scores):
		work = self.work[user]
		row = {
			"user": user,
			"storekeeper_name": names.get(user) or user,
			"warehouses": self._places(work),
			"transactions": len(work),
			"lines": sum(r["lines"] for r in work),
			"cancelled": len(self.cancelled[user]),
			"corrections": len(self.corrections[user]),
			"amended": len(self.amended[user]),
			"latest_score": scores.get(user),
		}
		for key, _label, txn_type in TYPE_COLUMNS:
			row[key] = sum(1 for r in work if r["type"] == txn_type)
		for key, _label, field in ROW_COLUMNS:
			row[key] = sum(r[field] for r in work)
		return row

	def _places(self, work):
		places = set()
		for r in work:
			places.update(r["warehouses"] or [])
			places.update(r["locations"] or [])
		return ", ".join(sorted(places))

	def _latest_scores(self):
		"""Latest submitted score overlapping the period, else the latest submitted overall."""
		if not self.users:
			return {}
		scope_sql, params = "", {"users": self.users}
		if self.ctx["allowed_warehouses"]:
			scope_sql, params["whs"] = "AND warehouse IN %(whs)s", self.ctx["allowed_warehouses"]
		evals = frappe.db.sql(
			f"""SELECT storekeeper, overall_score, from_date, to_date FROM `tabWarehouse Staff Evaluation`
			WHERE docstatus = 1 AND storekeeper IN %(users)s {scope_sql}
			ORDER BY to_date DESC, creation DESC""",
			params,
			as_dict=True,
		)
		overlapping, latest = {}, {}
		for e in evals:
			latest.setdefault(e.storekeeper, e.overall_score)
			if str(e.from_date) <= self.f.to_date and str(e.to_date) >= self.f.from_date:
				overlapping.setdefault(e.storekeeper, e.overall_score)
		return {u: overlapping.get(u, latest.get(u)) for u in self.users if u in latest}

	@staticmethod
	def _int(fieldname, label):
		return {"fieldname": fieldname, "label": label, "fieldtype": "Int", "width": 120}


def _group(rows, key):
	groups = defaultdict(list)
	for r in rows:
		groups[r[key]].append(r)
	return groups


def _full_names(users):
	if not users:
		return {}
	found = frappe.get_all("User", filters={"name": ["in", list(users)]}, fields=["name", "full_name"])
	return {u.name: (u.full_name or "").strip() for u in found}
