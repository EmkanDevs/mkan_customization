"""Script Report: Warehouse Staff Transaction Detail (spec 6.5).

One row per document. Scope and source rows come from the shared scope.resolve and
load_activity. Row selection (type, MR type, special) is done here.
"""
import frappe

from mkan_customization.warehouse_kpi import scope
from mkan_customization.warehouse_kpi.sources import load_activity
from mkan_customization.warehouse_kpi.txn_types import EQUIPMENT_LOG, MR_CREATED, MR_ISSUED, OPENING

# A "Special" pick fixes the status, so the status filter cannot hide what it asks for.
SPECIAL_STATUS = {"Cancelled": "Cancelled", "Corrections": "Submitted", "Amended by user": "Submitted", "Opening": "Submitted"}


def execute(filters=None):
	report = TransactionDetail(filters)
	return report.columns(), report.data()


class TransactionDetail:
	def __init__(self, filters):
		filters = frappe._dict(filters or {})
		self.special = filters.get("special") or ""
		if self.special and self.special not in SPECIAL_STATUS:
			frappe.throw("Invalid Special filter.")
		if self.special:
			filters["status"] = SPECIAL_STATUS[self.special]
		self.txn_type = filters.get("transaction_type") or ""
		self.mr_type = filters.get("mr_type") or ""
		self.ctx = scope.resolve(filters)
		self.query, self.rows = load_activity(self.ctx)

	def columns(self):
		return [
			{"fieldname": "name", "label": "Document", "fieldtype": "Dynamic Link", "options": "doctype", "width": 170},
			{"fieldname": "doctype", "label": "Doctype", "fieldtype": "Data", "width": 150},
			{"fieldname": "type", "label": "Type", "fieldtype": "Data", "width": 190},
			{"fieldname": "stock_entry_type", "label": "Stock Entry Type", "fieldtype": "Data", "width": 150},
			{"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
			{"fieldname": "user", "label": "Created By", "fieldtype": "Link", "options": "User", "width": 180},
			{"fieldname": "place", "label": "Warehouse / Location", "fieldtype": "Data", "width": 190},
			{"fieldname": "target", "label": "Target", "fieldtype": "Data", "width": 150},
			{"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 90},
			{"fieldname": "lines", "label": "Item Lines", "fieldtype": "Int", "width": 90},
			{"fieldname": "txn_qty", "label": "Transaction Qty + UOM", "fieldtype": "Data", "width": 170},
			{"fieldname": "stock_qty", "label": "Stock Qty + UOM", "fieldtype": "Data", "width": 170},
			{"fieldname": "mr_type", "label": "MR Type", "fieldtype": "Data", "width": 130},
			{"fieldname": "ref", "label": "Return Request", "fieldtype": "Data", "width": 150},
			{"fieldname": "amended_from", "label": "Amended From", "fieldtype": "Data", "width": 150},
			{"fieldname": "original_owner", "label": "Original Creator", "fieldtype": "Link", "options": "User", "width": 180},
		]

	def data(self):
		return [self._line(r) for r in self._selected()]

	def _selected(self):
		users = set(self.query.users)
		rows = [r for r in self.rows if self._in_special(r, users)]
		if self.txn_type:
			rows = [r for r in rows if r["type"] == self.txn_type]
		if self.mr_type:
			rows = [r for r in rows if r["type"] in (MR_CREATED, MR_ISSUED) and r["mr_type"] == self.mr_type]
		return rows

	def _in_special(self, r, users):
		"""Same membership rules as the dashboard drills. Opening entries show only under Special."""
		if self.special == "Opening":
			return r["type"] == OPENING and r["docstatus"] == 1 and r["user"] in users
		if r["type"] == OPENING:
			return False
		if self.special == "Corrections":
			return r["docstatus"] == 1 and bool(r["amended_from"]) and r["original_owner"] in users
		if r["user"] not in users:
			return False
		if self.special == "Amended by user":
			return r["docstatus"] == 1 and bool(r["amended_from"])
		if self.special == "Cancelled":
			return r["docstatus"] == 2
		return True

	def _line(self, r):
		return {
			"name": r["name"],
			"doctype": r["doctype"],
			"type": _type_label(r),
			"stock_entry_type": r["stock_entry_type"],
			"date": r["date"],
			"user": r["user"],
			"place": ", ".join(r["warehouses"] or r["locations"] or []),
			"target": ", ".join(r["targets"] or []),
			"status": "Cancelled" if r["docstatus"] == 2 else "Submitted",
			"lines": r["lines"],
			"txn_qty": _qty_text(r["txn_uom_qty"]),
			"stock_qty": _qty_text(r["stock_uom_qty"]),
			"mr_type": r["mr_type"],
			"ref": r["ref"],
			"amended_from": r["amended_from"],
			"original_owner": r["original_owner"],
		}


def _type_label(r):
	detail = r["elr_type"] if r["type"] == EQUIPMENT_LOG else None
	return f"{r['type']} ({detail})" if detail else r["type"]


def _qty_text(per_uom):
	return ", ".join(f"{qty:,.2f}".rstrip("0").rstrip(".") + f" {uom}" for uom, qty in per_uom.items())
