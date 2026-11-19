"""Stock Differences tab (spec 4.8). Source: submitted Stock Reconciliation, purpose 'Stock Reconciliation'."""
from collections import OrderedDict

import frappe
from frappe.utils import flt

from mkan_customization.warehouse_kpi.metrics import _full_names

MAX_PAGE = 100


def get_differences(query, summary_page, detail_page):
	lines = get_lines(query)
	return {
		"bars": _bars(lines),
		"summary": _page(_monthly(lines), summary_page),
		"details": _page(lines, detail_page),
	}


def get_lines(query):
	"""All item-level difference lines for the filters (no paging). Also used by the Excel export."""
	lines = _load_lines(query)
	names = _full_names({r["owner"] for r in lines})
	for r in lines:
		r["owner_name"] = names.get(r["owner"]) or r["owner"]
	return lines


def _load_lines(q):
	if q.location or not q.users:  # a location filter hides stock documents
		return []
	conds, params = _conditions(q)
	rows = frappe.db.sql(
		f"""SELECT t.name, t.posting_date, t.owner, i.idx, i.item_code, i.item_name, i.warehouse, i.stock_uom,
			i.current_qty, i.qty, i.quantity_difference, i.amount_difference
		FROM `tabStock Reconciliation` t JOIN `tabStock Reconciliation Item` i ON i.parent = t.name
		WHERE {" AND ".join(conds)}
		ORDER BY t.posting_date DESC, t.name DESC, i.idx""",
		params,
		as_dict=True,
	)
	return [_line(r) for r in rows]


def _conditions(q):
	conds = [
		"t.docstatus = 1",
		"t.purpose = 'Stock Reconciliation'",
		"t.posting_date BETWEEN %(from_date)s AND %(to_date)s",
		"t.owner IN %(users)s",
	]
	params = {"from_date": q.from_date, "to_date": q.to_date, "users": q.users}
	if q.company:
		conds.append("t.company = %(company)s")
		params["company"] = q.company
	if q.warehouse:
		conds.append("i.warehouse = %(warehouse)s")
		params["warehouse"] = q.warehouse
	if q.allowed_warehouses:
		conds.append("i.warehouse IN %(allowed)s")
		params["allowed"] = q.allowed_warehouses
	return conds, params


def _line(r):
	# quantity_difference is a varchar in ERPNext, so parse it; fall back to qty - current_qty.
	diff = flt(r.quantity_difference) if r.quantity_difference not in (None, "") else flt(r.qty) - flt(r.current_qty)
	return {
		"name": r.name,
		"date": str(r.posting_date),
		"owner": r.owner,
		"warehouse": r.warehouse,
		"item_code": r.item_code,
		"item_name": r.item_name,
		"uom": r.stock_uom,
		"erp_qty": flt(r.current_qty),
		"counted_qty": flt(r.qty),
		"difference": diff,
		"value": flt(r.amount_difference),
	}


def _bars(lines):
	totals = {}
	for r in lines:
		totals[r["warehouse"]] = totals.get(r["warehouse"], 0) + r["value"]
	return sorted(([w, round(v, 2)] for w, v in totals.items()), key=lambda x: -abs(x[1]))


def _monthly(lines):
	groups = OrderedDict()
	for r in lines:
		key = (r["date"][:7], r["warehouse"], r["owner"])
		g = groups.setdefault(key, {"month": key[0], "warehouse": key[1], "owner_name": r["owner_name"],
			"items_checked": 0, "difference_lines": 0, "value": 0})
		g["items_checked"] += 1
		g["difference_lines"] += 1 if r["difference"] else 0
		g["value"] += r["value"]
	rows = sorted(groups.values(), key=lambda g: (g["month"], g["warehouse"]), reverse=True)
	for g in rows:
		g["value"] = round(g["value"], 2)
	return rows


def _page(rows, page):
	page = page or {}
	limit = min(max(int(page.get("limit") or 10), 1), MAX_PAGE)
	offset = max(int(page.get("offset") or 0), 0)
	return {"total": len(rows), "rows": rows[offset : offset + limit]}

