import frappe
from frappe import _


DEPARTMENT_PROJECT_NAMES = {
	"Services Related to Operation and Production (Overhead)",
	"General and Administrative Expenses (G&A)",
}


def validate_item_dimensions(doc):
	projects = {}
	missing_departments = []
	for row in doc.get("items") or []:
		if not row.get("project") and doc.get("custom_project"):
			row.project = doc.custom_project
		project = _get_project(row.get("project"), projects)
		requires_department = (
			row.get("project") in DEPARTMENT_PROJECT_NAMES
			or project.get("project_name") in DEPARTMENT_PROJECT_NAMES
		)
		if not requires_department:
			row.department = None
		elif not row.get("department"):
			missing_departments.append(row.idx)

	if missing_departments:
		frappe.throw(
			_("Department is mandatory for row(s): {0}").format(
				", ".join(str(idx) for idx in missing_departments)
			)
		)
	_set_cost_centers(doc.get("items") or [], projects)


def _set_cost_centers(rows, projects):
	departments = {}
	for row in rows:
		department = row.get("department")
		project = row.get("project")
		if department and department not in departments:
			departments[department] = _get_department_cost_center(department)
		# Department cost center first, then the Project cost center.
		row.cost_center = (
			(department and departments[department])
			or (project and _get_project(project, projects).get("cost_center"))
			or None
		)


def _get_project(name, projects):
	if not name:
		return frappe._dict()
	if name not in projects:
		projects[name] = frappe.db.get_value(
			"Project", name, ["project_name", "cost_center"], as_dict=True
		) or frappe._dict()
	return projects[name]


@frappe.whitelist()
def get_row_cost_center(project=None, department=None):
	"""Return the cost center for a Material Request row: Department first, then Project."""
	frappe.has_permission("Material Request", "read", throw=True)
	return (
		(department and _get_department_cost_center(department))
		or (project and frappe.db.get_value("Project", project, "cost_center"))
		or None
	)


def _get_department_cost_center(department):
	# The add_department_cost_center patch skips "cost_center" on sites that already have "custom_cost_center".
	meta = frappe.get_meta("Department")
	fieldname = "cost_center" if meta.has_field("cost_center") else "custom_cost_center"
	if not meta.has_field(fieldname):
		return None
	return frappe.db.get_value("Department", department, fieldname)
