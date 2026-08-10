import frappe
from frappe.utils import cint, getdate, get_last_day

FILTER_ALL = "All"
STATE_PENDING_APPROVAL = "Pending Approval"
DEFAULT_PAGE_LENGTH = 50
MAX_PAGE_LENGTH = 500


def _flt(value):
	"""Safe float conversion, defaults to 0."""
	return float(value or 0)


def _resolve_date_range(year=None, month=None, from_date=None, to_date=None):
	"""
	Resolve an effective from_date/to_date.

	Explicit from_date/to_date (if supplied) always win, so that filtering
	uses indexed BETWEEN-style comparisons on posting_date rather than
	YEAR()/MONTH() wrapping the column (which prevents index usage).
	"""
	if from_date or to_date:
		return from_date, to_date

	if not year:
		return from_date, to_date

	year = cint(year)

	if month and str(month) != FILTER_ALL:
		month = cint(month)
		start = getdate(f"{year}-{month:02d}-01")
		end = get_last_day(start)
		return start, end

	return getdate(f"{year}-01-01"), getdate(f"{year}-12-31")


def _get_conditions(company=None, from_date=None, to_date=None, custodian=None, project=None):
	"""
	Shared WHERE-clause builder used by both the dashboard and grid endpoints.
	Returns (where_clause, params).
	"""
	conditions = ["pr.is_petty_cash = 1", "pr.docstatus != 2"]
	params = {}

	if company:
		conditions.append("pr.company = %(company)s")
		params["company"] = company
	if from_date:
		conditions.append("pr.posting_date >= %(from_date)s")
		params["from_date"] = from_date
	if to_date:
		conditions.append("pr.posting_date <= %(to_date)s")
		params["to_date"] = to_date
	if custodian and custodian != FILTER_ALL:
		conditions.append("pr.petty_cash_employee = %(custodian)s")
		params["custodian"] = custodian
	if project and project != FILTER_ALL:
		conditions.append("pr.project = %(project)s")
		params["project"] = project

	return " AND ".join(conditions), params


@frappe.whitelist()
def get_dashboard_data(company=None, year=None, month=None, from_date=None, to_date=None, custodian=None, project=None):
	"""
	Returns all dashboard data: KPIs, charts, and grid data.
	Called from the Petty Cash Executive Dashboard page.
	"""
	try:
		from_date, to_date = _resolve_date_range(year, month, from_date, to_date)
		where_clause, params = _get_conditions(company, from_date, to_date, custodian, project)

		# ── KPIs ──
		kpis = frappe.db.sql(f"""
			SELECT
				IFNULL(SUM(pr.grand_total), 0) AS total_spent,
				IFNULL(SUM(pr.total_taxes_and_charges), 0) AS total_tax,
				COUNT(*) AS total_receipts,
				IFNULL(AVG(pr.grand_total), 0) AS avg_receipt,
				COUNT(DISTINCT pr.petty_cash_employee) AS active_custodians
			FROM `tabPurchase Receipt` pr
			WHERE {where_clause}
		""", params, as_dict=True)[0]

		# ── Pending ──
		pending = frappe.db.sql(f"""
			SELECT
				COUNT(*) AS pending_count,
				IFNULL(SUM(pr.grand_total), 0) AS pending_amount
			FROM `tabPurchase Receipt` pr
			WHERE {where_clause} AND pr.workflow_state = %(pending_state)s
		""", {**params, "pending_state": STATE_PENDING_APPROVAL}, as_dict=True)[0]

		# ── Top Custodian ──
		top_custodian_rows = frappe.db.sql(f"""
			SELECT
				COALESCE(pr.custom_petty_cash_holder_name, pr.petty_cash_employee) AS custodian,
				IFNULL(SUM(pr.grand_total), 0) AS amount
			FROM `tabPurchase Receipt` pr
			WHERE {where_clause}
			GROUP BY pr.petty_cash_employee, pr.custom_petty_cash_holder_name
			ORDER BY amount DESC
			LIMIT 1
		""", params, as_dict=True)
		top_custodian = top_custodian_rows[0] if top_custodian_rows else {"custodian": "—", "amount": 0}

		# ── Total Quantity ──
		qty_result = frappe.db.sql(f"""
			SELECT IFNULL(SUM(pri.qty), 0) AS total_qty
			FROM `tabPurchase Receipt` pr
			LEFT JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
			WHERE {where_clause}
		""", params, as_dict=True)[0]

		# ── Custodian Chart ──
		custodian_chart = frappe.db.sql(f"""
			SELECT
				COALESCE(pr.custom_petty_cash_holder_name, pr.petty_cash_employee) AS label,
				IFNULL(SUM(pr.grand_total), 0) AS value
			FROM `tabPurchase Receipt` pr
			WHERE {where_clause}
			GROUP BY pr.petty_cash_employee, pr.custom_petty_cash_holder_name
			ORDER BY value DESC
		""", params, as_dict=True)

		# ── Project Chart ──
		project_chart = frappe.db.sql(f"""
			SELECT
				COALESCE(prj.project_name, pr.project) AS label,
				IFNULL(SUM(pr.grand_total), 0) AS value
			FROM `tabPurchase Receipt` pr
			LEFT JOIN `tabProject` prj ON prj.name = pr.project
			WHERE {where_clause}
			GROUP BY pr.project, prj.project_name
			ORDER BY value DESC
		""", params, as_dict=True)

		# ── Vendor Chart ──
		vendor_chart = frappe.db.sql(f"""
			SELECT
				COALESCE(pr.supplier_name, pr.supplier) AS label,
				IFNULL(SUM(pr.grand_total), 0) AS value
			FROM `tabPurchase Receipt` pr
			WHERE {where_clause}
			GROUP BY pr.supplier, pr.supplier_name
			ORDER BY value DESC
			LIMIT 10
		""", params, as_dict=True)

		# ── Monthly Trend ──
		trend_chart = frappe.db.sql(f"""
			SELECT
				DATE_FORMAT(pr.posting_date, '%%b %%Y') AS label,
				IFNULL(SUM(pr.grand_total), 0) AS value
			FROM `tabPurchase Receipt` pr
			WHERE {where_clause}
			GROUP BY YEAR(pr.posting_date), MONTH(pr.posting_date)
			ORDER BY YEAR(pr.posting_date), MONTH(pr.posting_date)
		""", params, as_dict=True)

		# ── Workflow Status ──
		status_chart = frappe.db.sql(f"""
			SELECT
				pr.workflow_state AS label,
				COUNT(*) AS value
			FROM `tabPurchase Receipt` pr
			WHERE {where_clause}
			GROUP BY pr.workflow_state
		""", params, as_dict=True)

		return {
			"kpis": {
				"total_spent": _flt(kpis.get("total_spent")),
				"total_tax": _flt(kpis.get("total_tax")),
				"total_receipts": cint(kpis.get("total_receipts")),
				"avg_receipt": _flt(kpis.get("avg_receipt")),
				"active_custodians": cint(kpis.get("active_custodians")),
				"net_total": _flt(kpis.get("total_spent")) - _flt(kpis.get("total_tax")),
				"pending_count": cint(pending.get("pending_count")),
				"pending_amount": _flt(pending.get("pending_amount")),
				"top_custodian": top_custodian,
				"total_qty": _flt(qty_result.get("total_qty")),
			},
			"custodian_chart": custodian_chart,
			"project_chart": project_chart,
			"vendor_chart": vendor_chart,
			"trend_chart": trend_chart,
			"status_chart": status_chart,
		}
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Petty Cash Dashboard: get_dashboard_data failed")
		raise


@frappe.whitelist()
def get_receipts_grid(company=None, year=None, month=None, from_date=None, to_date=None,
                       custodian=None, project=None, search_term=None, start=0, page_length=DEFAULT_PAGE_LENGTH):
	"""
	Returns paginated Purchase Receipt data for the Live Log grid.
	"""
	try:
		from_date, to_date = _resolve_date_range(year, month, from_date, to_date)
		where_clause, params = _get_conditions(company, from_date, to_date, custodian, project)

		start = max(0, cint(start))
		page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
		params["start"] = start
		params["page_length"] = page_length

		search_condition = ""
		if search_term:
			search_condition = """ AND (
				pr.name LIKE %(search)s
				OR pr.custom_petty_cash_holder_name LIKE %(search)s
				OR pr.supplier_name LIKE %(search)s
				OR pr.project LIKE %(search)s
				OR prj.project_name LIKE %(search)s
			)"""
			params["search"] = f"%{search_term}%"

		data = frappe.db.sql(f"""
			SELECT
				pr.name AS purchase_receipt,
				pr.posting_date,
				pr.custom_petty_cash_holder_name AS custody_employee,
				pr.supervisor AS custody_manager,
				pr.supplier_name,
				COALESCE(prj.project_name, pr.project) AS project_name,
				pr.total_taxes_and_charges AS tax_amount,
				pr.grand_total,
				pr.workflow_state
			FROM `tabPurchase Receipt` pr
			LEFT JOIN `tabProject` prj ON prj.name = pr.project
			WHERE {where_clause} {search_condition}
			ORDER BY pr.posting_date DESC, pr.creation DESC
			LIMIT %(page_length)s OFFSET %(start)s
		""", params, as_dict=True)

		# Batch-fetch item descriptions for every receipt on this page in a
		# single query instead of one query per row (fixes the N+1 problem).
		receipt_names = [row.purchase_receipt for row in data]
		item_map = {}
		if receipt_names:
			# NOTE: the aggregated column is deliberately NOT aliased "items" —
			# frappe.db.sql(as_dict=True) rows are dict subclasses, and dict
			# already has a built-in .items() method. Attribute access on a
			# key called "items" would silently return that bound method
			# instead of the value, so we use "item_list" and subscript access.
			item_rows = frappe.db.sql("""
				SELECT parent, GROUP_CONCAT(description SEPARATOR ', ') AS item_list
				FROM `tabPurchase Receipt Item`
				WHERE parent IN %(parents)s
				GROUP BY parent
			""", {"parents": tuple(receipt_names)}, as_dict=True)
			item_map = {row["parent"]: row["item_list"] for row in item_rows}

		for row in data:
			row["items"] = item_map.get(row.purchase_receipt) or "—"
			row["posting_date"] = frappe.format_value(row["posting_date"], {"fieldtype": "Date"})

		count_params = {k: v for k, v in params.items() if k not in ("start", "page_length")}
		total = frappe.db.sql(f"""
			SELECT COUNT(*) AS total
			FROM `tabPurchase Receipt` pr
			LEFT JOIN `tabProject` prj ON prj.name = pr.project
			WHERE {where_clause} {search_condition}
		""", count_params, as_dict=True)[0].get("total", 0)

		return {"data": data, "total": cint(total)}
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Petty Cash Dashboard: get_receipts_grid failed")
		raise


@frappe.whitelist()
def get_filter_options():
	"""
	Returns dropdown options for filters.
	"""
	try:
		custodians = frappe.db.sql("""
			SELECT name, employee_name
			FROM `tabPetty Cash Authorized Employees`
			WHERE status = 'Active'
			ORDER BY employee_name
		""", as_dict=True)

		projects = frappe.db.sql("""
			SELECT name, project_name
			FROM `tabProject`
			WHERE status = 'Open'
			ORDER BY project_name
		""", as_dict=True)

		companies = frappe.db.sql("""
			SELECT name FROM `tabCompany` ORDER BY name
		""", as_dict=True)

		return {
			"custodians": custodians,
			"projects": projects,
			"companies": companies,
		}
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Petty Cash Dashboard: get_filter_options failed")
		raise