"""Whitelisted methods for the Warehouse Staff Performance page (spec 6.3)."""
import frappe
from frappe import _
from frappe.utils import cint

from mkan_customization.warehouse_kpi import differences, evaluations, export, scope, summary
from mkan_customization.warehouse_kpi.scope import MANAGER_ROLE, STOREKEEPER_ROLE
from mkan_customization.warehouse_kpi.metrics import Metrics, serialize_rows
from mkan_customization.warehouse_kpi.performance import Performance
from mkan_customization.warehouse_kpi.sources import ActivityQuery, load_activity

ALLOWED_ROLES = (STOREKEEPER_ROLE, MANAGER_ROLE, "System Manager")
MAX_PAGE_SIZE = 100


@frappe.whitelist()
def get_page_context():
	"""Role flags and UI settings. The UI only hides things; the server enforces."""
	_check_access()
	roles = frappe.get_roles()
	privileged = MANAGER_ROLE in roles or "System Manager" in roles
	company = frappe.defaults.get_user_default("Company")
	return {
		"is_storekeeper_only": not privileged,
		"can_evaluate": privileged,
		"company": company,
		"currency": frappe.get_cached_value("Company", company, "default_currency") if company else "",
	}


@frappe.whitelist()
def get_dashboard(filters=None):
	ctx, metrics = _load(filters)
	data = metrics.dashboard(ctx["filters"].from_date, ctx["filters"].to_date)
	data["filters"] = {"from_date": ctx["filters"].from_date, "to_date": ctx["filters"].to_date}
	return data


@frappe.whitelist()
def get_transactions(filters=None, drill=None, limit=10, offset=0):
	_, metrics = _load(filters)
	rows = metrics.drill(drill)
	limit = min(max(cint(limit), 1), MAX_PAGE_SIZE)
	offset = max(cint(offset), 0)
	return {"total": len(rows), "rows": serialize_rows(rows[offset : offset + limit])}


@frappe.whitelist()
def get_document_summary(doctype, name):
	_check_access()
	return summary.get_summary(doctype, name)


@frappe.whitelist()
def get_performance(filters=None, limit=10, offset=0):
	return _performance(filters).table(_limit(limit), max(cint(offset), 0))


@frappe.whitelist()
def get_drill_docs(filters=None, user=None, act=None, limit=10, offset=0):
	perf = _performance(filters)
	if user not in perf.users:  # also blocks a storekeeper asking for someone else
		frappe.throw(_("User is not in your scope."), frappe.PermissionError)
	rows = perf.user_rows(user, act)
	limit, offset = _limit(limit), max(cint(offset), 0)
	return {"total": len(rows), "rows": serialize_rows(rows[offset : offset + limit])}


@frappe.whitelist()
def get_stock_differences(filters=None, summary_page=None, detail_page=None):
	_check_access()
	ctx = scope.resolve(filters)
	query = ActivityQuery(ctx)
	return differences.get_differences(query, frappe.parse_json(summary_page), frappe.parse_json(detail_page))


@frappe.whitelist()
def get_reconciliation(name):
	_check_access()
	return summary.get_summary("Stock Reconciliation", name)


@frappe.whitelist()
def get_evaluations(filters=None):
	_check_access()
	return evaluations.list_evaluations(filters)


@frappe.whitelist()
def get_evaluation(name):
	_check_access()
	return evaluations.get_evaluation(name)


@frappe.whitelist()
def get_evaluation_form():
	_check_access()
	return evaluations.get_form_data()


@frappe.whitelist(methods=["POST"])
def save_evaluation(data, submit=0):
	_check_access()
	return evaluations.save_evaluation(data, submit)


@frappe.whitelist()
def export_excel(filters=None):
	"""Download the five-sheet workbook for the same filters and scope as the screen."""
	_check_access()
	filename, content = export.build_export(filters)
	frappe.response["filename"] = filename
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"


def _performance(filters):
	_check_access()
	ctx = scope.resolve(filters)
	query, rows = load_activity(ctx)
	f = ctx["filters"]
	return Performance(Metrics(rows, query.users), query.users, ctx["allowed_warehouses"], f.from_date, f.to_date)


def _limit(limit):
	return min(max(cint(limit), 1), MAX_PAGE_SIZE)


def _load(filters):
	_check_access()
	ctx = scope.resolve(filters)
	query, rows = load_activity(ctx)
	return ctx, Metrics(rows, query.users)


def _check_access():
	if not set(ALLOWED_ROLES) & set(frappe.get_roles()):
		frappe.throw(_("You are not permitted to view this page."), frappe.PermissionError)
