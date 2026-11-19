from frappe.utils import flt

# Project.update_costing() (ERPNext, and the HRMS EmployeeProject override) assigns
# SUM() results straight to these fields. With no submitted Timesheets / Expense
# Claims, SUM() returns NULL, so the doc holds None while the DB holds 0. The
# Version diff then logs "changed from 0 to null" on every save. Coerce back to 0.
NULLABLE_COSTING_FIELDS = (
	"actual_time",
	"total_costing_amount",
	"total_billable_amount",
	"total_expense_claim",
)


def fix_null_costing(doc, method=None):
	for field in NULLABLE_COSTING_FIELDS:
		if doc.meta.has_field(field):
			doc.set(field, flt(doc.get(field)))
