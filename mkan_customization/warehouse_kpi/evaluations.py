"""Evaluations tab backend. All rules live in the doctype controller; this only moves data."""
import frappe
from frappe import _
from frappe.utils import cint, get_first_day, get_last_day, nowdate

from mkan_customization.warehouse_kpi import scope
from mkan_customization.warehouse_kpi.scope import MANAGER_ROLE
from mkan_customization.warehouse_kpi.doctype.warehouse_staff_evaluation_settings.warehouse_staff_evaluation_settings import (
	DEFAULT_QUESTIONS,
)

DOCTYPE = "Warehouse Staff Evaluation"
RATINGS = ("1", "2", "3", "4", "5")


def list_evaluations(filters):
	ctx = scope.resolve(filters)
	f = ctx["filters"]
	conds = {"docstatus": ["in", [0, 1]], "from_date": ["<=", f.to_date], "to_date": [">=", f.from_date]}
	if f.get("warehouse"):
		conds["warehouse"] = f.warehouse
	if f.get("storekeeper"):
		conds["storekeeper"] = f.storekeeper
	if ctx["own_view"]:  # only the user's own submitted evaluations
		conds.update(docstatus=1, storekeeper=frappe.session.user)
	if ctx["allowed_warehouses"]:
		conds.setdefault("warehouse", ["in", ctx["allowed_warehouses"]])
	rows = frappe.get_list(  # a storekeeper has no doctype access; own_view above limits the rows
		DOCTYPE,
		ignore_permissions=bool(ctx["own_view"]),
		filters=conds,
		fields=["name", "storekeeper", "storekeeper_name", "warehouse", "from_date", "to_date", "docstatus", "overall_score"],
		order_by="from_date desc, creation desc",
		limit_page_length=200,
	)
	return rows


def get_evaluation(name):
	doc = frappe.get_doc(DOCTYPE, name)
	_check_readable(doc)
	evaluator = frappe.db.get_value("User", doc.evaluated_by, "full_name") if doc.evaluated_by else None
	ratings = [{"question": r.question, "rating": cint(r.rating), "remarks": r.remarks} for r in doc.ratings]
	return {
		"name": doc.name,
		"storekeeper": doc.storekeeper,
		"storekeeper_name": doc.storekeeper_name,
		"warehouse": doc.warehouse,
		"from_date": str(doc.from_date),
		"to_date": str(doc.to_date),
		"docstatus": doc.docstatus,
		"overall_score": doc.overall_score,
		"score_percent": doc.score_percent,
		"complete": bool(ratings) and all(r["rating"] for r in ratings),
		"remarks": doc.overall_remarks,
		"evaluated_by": evaluator or doc.evaluated_by,
		"ratings": ratings,
		"can_edit": doc.docstatus == 0 and doc.has_permission("write"),
	}


def get_form_data():
	"""Questions and defaults for the New Evaluation dialog."""
	_require_evaluator()
	settings = frappe.get_cached_doc("Warehouse Staff Evaluation Settings")
	questions = [q.question for q in settings.questions if q.is_active] or list(DEFAULT_QUESTIONS)
	today = nowdate()
	return {
		"questions": questions,
		"company": frappe.defaults.get_user_default("Company"),
		"allowed_warehouses": scope.resolve({})["allowed_warehouses"],
		"from_date": str(get_first_day(today)),
		"to_date": str(get_last_day(today)),
	}


def save_evaluation(data, submit=0):
	_require_evaluator()
	data = frappe.parse_json(data)
	doc = _load_or_new(data)
	_apply(doc, data)
	if cint(submit):
		_check_complete(doc)
	doc.insert() if doc.is_new() else doc.save()
	if cint(submit):
		doc.submit()
	return doc.name


def _load_or_new(data):
	if data.get("name"):
		doc = frappe.get_doc(DOCTYPE, data["name"])
		if doc.docstatus != 0:
			frappe.throw(_("Only draft evaluations can be edited here."))
		return doc
	doc = frappe.new_doc(DOCTYPE)
	doc.company = data.get("company") or frappe.defaults.get_user_default("Company")
	doc.populate_questions_snapshot()
	return doc


def _apply(doc, data):
	for field in ("storekeeper", "warehouse", "from_date", "to_date", "overall_remarks"):
		doc.set(field, data.get(field))
	by_question = {r.get("question"): r for r in data.get("ratings") or []}
	for row in doc.ratings:
		given = by_question.get(row.question) or {}
		rating = str(given.get("rating") or "")
		if rating and rating not in RATINGS:
			frappe.throw(_("Rating must be between 1 and 5."))
		row.rating = rating or None
		row.remarks = given.get("remarks") or ""


def _check_readable(doc):
	"""Managers use doctype permissions. A storekeeper may read only their own submitted evaluation."""
	if {MANAGER_ROLE, "System Manager"} & set(frappe.get_roles()):
		doc.check_permission("read")
	elif not (doc.docstatus == 1 and doc.storekeeper == frappe.session.user):
		frappe.throw(_("Not permitted."), frappe.PermissionError)


def _check_complete(doc):
	for row in doc.ratings:
		if row.rating not in RATINGS:
			frappe.throw(_("Please rate '{0}' before submitting.").format(row.question))


def _require_evaluator():
	roles = set(frappe.get_roles())
	if not {MANAGER_ROLE, "System Manager"} & roles:
		frappe.throw(_("Only Stock Managers can evaluate."), frappe.PermissionError)
