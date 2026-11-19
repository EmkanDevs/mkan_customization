"""Excel export (spec 6.7): five sheets built from the same data as the page, in the same scope."""
from io import BytesIO

import frappe
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from mkan_customization.warehouse_kpi import differences, evaluations, scope
from mkan_customization.warehouse_kpi.metrics import Metrics, _full_names, _qty_text, _type_label
from mkan_customization.warehouse_kpi.performance import Performance
from mkan_customization.warehouse_kpi.sources import load_activity
from mkan_customization.warehouse_kpi.txn_types import ISSUED_TYPES, RECEIVED_TYPES, TRANSFERRED_TYPES

DEFAULT_ROW_LIMIT = 50000
SUMMARY_COLUMNS = [
	("transactions", "Transactions"), ("lines", "Item Lines"),
	("purchase_receipts", "Purchase Receipts"), ("material_returns", "Material Returns"),
	("return_requests", "Return Requests"), ("petty_cash", "Petty Cash"), ("other_receipts", "Other Receipts"),
	("material_issues", "Material Issues"), ("supplier_returns", "Supplier Returns"), ("transfers", "Transfers"),
	("stock_adjustments", "Stock Adjustments"), ("mr_created", "MR Created"), ("mr_issued", "MR Issued"),
	("equipment_logs", "Equipment Logs"), ("assets", "Assets"), ("light_equipment", "Light Equipment"),
	("cancelled", "Cancelled"), ("corrections", "Corrections"), ("amended", "Amended By User"),
]


def build_export(filters):
	"""Return (file name, xlsx bytes)."""
	ctx = scope.resolve(filters)
	query, rows = load_activity(ctx)
	f = ctx["filters"]
	metrics = Metrics(rows, query.users)
	perf = Performance(metrics, query.users, ctx["allowed_warehouses"], f.from_date, f.to_date)
	names = _full_names({r["user"] for r in metrics.rows} | set(query.users))

	book = Workbook()
	book.remove(book.active)
	_summary(book, perf)
	_received_issued(book, metrics, names)
	_transactions(book, metrics, names)
	_differences(book, differences.get_lines(query))
	_evaluations(book, evaluations.list_evaluations(filters))

	out = BytesIO()
	book.save(out)
	return f"CPC_Warehouse_Staff_Performance_{f.from_date}_to_{f.to_date}.xlsx", out.getvalue()


def _summary(book, perf):
	head = ["Stock User", "Warehouses / Locations", *[h for _, h in SUMMARY_COLUMNS], "Latest Evaluation"]
	table = perf.table(max(len(perf.users), 1), 0)["rows"]
	data = [
		[r["storekeeper_name"], r["warehouses"], *[r[k] for k, _ in SUMMARY_COLUMNS], r["latest_score"]]
		for r in table
	]
	_sheet(book, "Summary", head, data)


def _received_issued(book, metrics, names):
	buckets = {"received": RECEIVED_TYPES, "issued": ISSUED_TYPES, "transferred": TRANSFERRED_TYPES}
	totals = {}
	for r in metrics.work:
		for bucket, types in buckets.items():
			if r["type"] in types:
				for uom, qty in r["stock_uom_qty"].items():
					totals.setdefault((r["user"], uom), dict.fromkeys(buckets, 0))[bucket] += qty
	data = [
		[names.get(user) or user, uom, v["received"], v["issued"], v["transferred"]]
		for (user, uom), v in sorted(totals.items(), key=lambda x: ((names.get(x[0][0]) or "").lower(), x[0][1]))
	]
	_sheet(book, "Received and Issued", ["Stock User", "UOM", "Received", "Issued", "Transferred"], data)


def _transactions(book, metrics, names):
	limit = frappe.conf.get("warehouse_kpi_export_row_limit") or DEFAULT_ROW_LIMIT
	rows = metrics.rows
	note = None
	if len(rows) > limit:
		note = f"Only the first {limit} of {len(rows)} rows are shown. Narrow the date range or filters."
		rows = rows[:limit]
	head = [
		"Document", "Doctype", "Type", "Stock Entry Type", "Date", "Created By", "Warehouse or Location", "Target",
		"Status", "Item Lines", "Transaction Qty", "Stock Qty", "MR Type", "Return Request", "Amended From",
		"Original Creator",
	]
	data = [_transaction_row(r, names) for r in rows]
	_sheet(book, "Transactions", head, data, note=note)


def _transaction_row(r, names):
	source = ", ".join([*r["warehouses"], *r["locations"]])
	original = r["original_owner"]
	return [
		r["name"], r["doctype"], _type_label(r), r["stock_entry_type"], r["date"], names.get(r["user"]) or r["user"],
		source, ", ".join(r["targets"]), "Cancelled" if r["docstatus"] == 2 else "Submitted", r["lines"],
		_qty_text(r["txn_uom_qty"]), _qty_text(r["stock_uom_qty"]), r["mr_type"], r["ref"], r["amended_from"],
		(names.get(original) or original) if original else None,
	]


def _differences(book, lines):
	head = ["Reconciliation", "Date", "Warehouse", "Item Code", "Item Name", "UOM", "ERP Qty", "Counted Qty",
		"Difference Qty", "Difference Value", "Created By"]
	data = [
		[r["name"], r["date"], r["warehouse"], r["item_code"], r["item_name"], r["uom"], r["erp_qty"],
			r["counted_qty"], r["difference"], r["value"], r["owner_name"]]
		for r in lines
	]
	_sheet(book, "Stock Differences", head, data)


def _evaluations(book, listed):
	docs = [evaluations.get_evaluation(r.name) for r in listed]
	questions = []
	for d in docs:
		questions.extend(r["question"] for r in d["ratings"] if r["question"] not in questions)
	head = ["ID", "Stock User", "Warehouse", "From", "To", "Status", *questions, "Overall Score", "Remarks"]
	data = []
	for d in docs:
		given = {r["question"]: r["rating"] or None for r in d["ratings"]}
		data.append([
			d["name"], d["storekeeper_name"] or d["storekeeper"], d["warehouse"], d["from_date"], d["to_date"],
			"Submitted" if d["docstatus"] == 1 else "Draft", *[given.get(q) for q in questions],
			d["overall_score"], d["remarks"],
		])
	_sheet(book, "Evaluations", head, data)


def _sheet(book, title, head, data, note=None):
	ws = book.create_sheet(title)
	if note:
		ws.append([note])
		ws["A1"].font = Font(bold=True, color="C00000")
	ws.append(head)
	header_row = ws.max_row
	for cell in ws[header_row]:
		cell.font = Font(bold=True, color="FFFFFF")
		cell.fill = PatternFill("solid", fgColor="1E293B")
		cell.alignment = Alignment(wrap_text=True, vertical="center")
	for row in data:
		ws.append(row)
	ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
	for i, h in enumerate(head, 1):
		longest = max([len(str(h))] + [len(str(r[i - 1])) for r in data[:200] if r[i - 1] is not None])
		ws.column_dimensions[get_column_letter(i)].width = min(max(longest + 2, 10), 50)
