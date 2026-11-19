"""Performance Report: one row per storekeeper (spec 6.4), built from the same Metrics as the dashboard."""
from collections import defaultdict

import frappe

from mkan_customization.warehouse_kpi.metrics import _full_names
from mkan_customization.warehouse_kpi.txn_types import EQUIPMENT_LOG, MR_CREATED, MR_ISSUED

# column key -> transaction type
TYPE_COLUMNS = {
	"purchase_receipts": "Purchase Receipt",
	"material_returns": "Material Return",
	"return_requests": "Return Request",
	"petty_cash": "Petty Cash Receipt",
	"other_receipts": "Other Material Receipt",
	"material_issues": "Material Issue",
	"supplier_returns": "Supplier Return",
	"transfers": "Stock Transfer",
	"stock_adjustments": "Stock Adjustment",
	"mr_created": MR_CREATED,
	"mr_issued": MR_ISSUED,
	"equipment_logs": EQUIPMENT_LOG,
}
# Counted per ELR row, so the number can exceed the document count. Drill shows the documents.
ROW_COLUMNS = {"assets": "assets", "light_equipment": "light"}
OTHER_COLUMNS = ("transactions", "cancelled", "corrections", "amended")


class Performance:
	def __init__(self, metrics, users, allowed_warehouses, from_date, to_date):
		self.m = metrics
		self.users = sorted(users)
		self.allowed_warehouses = allowed_warehouses
		self.from_date, self.to_date = from_date, to_date

	def table(self, limit, offset):
		page = self.users[offset : offset + limit]
		names = _full_names(set(page))
		scores = self._latest_scores(page)
		work = self._group(self.m.work, "user")
		cancelled = self._group(self.m.cancelled, "user")
		corrections = self._group(self.m.corrections, "original_owner")
		amended = self._group(self.m.amended, "user")
		rows = [self._row(u, names, scores, work[u], cancelled[u], corrections[u], amended[u]) for u in page]
		rows.sort(key=lambda r: (r["storekeeper_name"] or "").lower())
		return {"total": len(self.users), "rows": rows}

	def user_rows(self, user, act):
		"""Documents behind one number of the table."""
		lists = {
			"transactions": (self.m.work, "user"),
			"cancelled": (self.m.cancelled, "user"),
			"corrections": (self.m.corrections, "original_owner"),
			"amended": (self.m.amended, "user"),
		}
		if act in lists:
			source, key = lists[act]
			return [r for r in source if r[key] == user]
		if act in ROW_COLUMNS:
			return [r for r in self.m.work if r["user"] == user and r[ROW_COLUMNS[act]] > 0]
		wanted = TYPE_COLUMNS.get(act)
		if not wanted:
			frappe.throw("Unknown column.")
		return [r for r in self.m.work if r["user"] == user and r["type"] == wanted]

	def _row(self, user, names, scores, work, cancelled, corrections, amended):
		row = {
			"storekeeper": user,
			"storekeeper_name": names.get(user) or user,
			"warehouses": self._places(work),
			"transactions": len(work),
			"lines": sum(r["lines"] for r in work),
			"cancelled": len(cancelled),
			"corrections": len(corrections),
			"amended": len(amended),
			"latest_score": scores.get(user),
		}
		for key, txn_type in TYPE_COLUMNS.items():
			row[key] = sum(1 for r in work if r["type"] == txn_type)
		for key, field in ROW_COLUMNS.items():
			row[key] = sum(r[field] for r in work)
		return row

	def _places(self, work):
		places = []
		for r in work:
			places.extend(r["warehouses"] or [])
			places.extend(r["locations"] or [])
		return ", ".join(sorted(set(places)))

	@staticmethod
	def _group(rows, key):
		groups = defaultdict(list)
		for r in rows:
			groups[r[key]].append(r)
		return groups

	def _latest_scores(self, users):
		"""Latest submitted score overlapping the period, else the latest submitted overall."""
		if not users:
			return {}
		scope_sql, params = "", {"users": users}
		if self.allowed_warehouses:
			scope_sql, params["whs"] = "AND warehouse IN %(whs)s", self.allowed_warehouses
		rows = frappe.db.sql(
			f"""SELECT storekeeper, overall_score, from_date, to_date FROM `tabWarehouse Staff Evaluation`
			WHERE docstatus = 1 AND storekeeper IN %(users)s {scope_sql}
			ORDER BY to_date DESC, creation DESC""",
			params,
			as_dict=True,
		)
		overlapping, latest = {}, {}
		for r in rows:
			latest.setdefault(r.storekeeper, r.overall_score)
			if str(r.from_date) <= self.to_date and str(r.to_date) >= self.from_date:
				overlapping.setdefault(r.storekeeper, r.overall_score)
		return {u: overlapping.get(u, latest.get(u)) for u in users if u in latest}
