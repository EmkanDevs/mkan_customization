import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate

# ERPNext's own roles stand in for the two evaluation roles. Change them here only.
STOREKEEPER_ROLE = "Stock User"
MANAGER_ROLE = "Stock Manager"


@frappe.whitelist()
def get_storekeeper_users_query(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	"""
	Link query for storekeeper selection: only enabled users with the storekeeper role (Stock User).
	"""
	return frappe.db.sql(
		"""
		SELECT u.name, u.full_name
		FROM `tabUser` u
		INNER JOIN `tabHas Role` r ON r.parent = u.name
		WHERE r.role = %(role)s
			AND u.enabled = 1
			AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.full_name ASC
		LIMIT %(start)s, %(page_len)s
		""",
		{"txt": f"%{txt}%", "start": start, "page_len": page_len, "role": STOREKEEPER_ROLE},
		as_dict=as_dict,
	)


def resolve(filters=None):
	"""
	Central permission and filter resolution engine (Spec 6.2).
	Must be called first in every API and report.
	"""
	if isinstance(filters, str):
		import json
		filters = json.loads(filters)
	filters = frappe._dict(filters or {})

	session_user = frappe.session.user
	user_roles = frappe.get_roles(session_user)
	is_system_manager = "System Manager" in user_roles
	is_warehouse_manager = MANAGER_ROLE in user_roles or is_system_manager
	is_storekeeper = STOREKEEPER_ROLE in user_roles and not is_warehouse_manager
	# "View as Stock User": a manager can narrow the page to their own records. It only
	# narrows, so any role may ask for it. The reverse is never possible.
	own_view = filters.get("view_as") == "Stock User"
	is_storekeeper = is_storekeeper or own_view

	# 1. Company
	if not filters.get("company"):
		filters.company = frappe.defaults.get_user_default("Company")

	# 2. Date validation
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if not from_date or not to_date:
		# Default to current month
		today = getdate(nowdate())
		filters.from_date = today.replace(day=1).strftime("%Y-%m-%d")
		filters.to_date = today.strftime("%Y-%m-%d")
	else:
		filters.from_date = str(from_date)
		filters.to_date = str(to_date)

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	max_days = 366
	if date_diff(filters.to_date, filters.from_date) > max_days:
		frappe.throw(
			_("Date range cannot exceed {0} days to protect system performance.").format(max_days)
		)

	# 3. Warehouse vs Location mutual exclusion (Spec 4.6)
	warehouse = filters.get("warehouse")
	location = filters.get("location")
	if warehouse and location:
		frappe.throw(_("Warehouse and Equipment Location filters cannot be applied at the same time."))

	# 4. Stock Manager permission & scope resolution (Spec 7.3)
	allowed_warehouses = []
	settings = frappe.get_single("Warehouse Staff Evaluation Settings")
	restrict_by_wh = getattr(settings, "restrict_manager_by_warehouse", 1)

	if not is_system_manager and restrict_by_wh:
		user_wh_perms = frappe.permissions.get_user_permissions(session_user).get("Warehouse", [])
		allowed_warehouses = [p.get("doc") for p in user_wh_perms if p.get("doc")]

		if allowed_warehouses:
			if warehouse and warehouse not in allowed_warehouses:
				frappe.throw(
					_("You do not have permission to view data for warehouse {0}.").format(
						frappe.bold(warehouse)
					),
					frappe.PermissionError,
				)

	# 5. Stock User restriction (Spec 6.2 step 3)
	if is_storekeeper:
		filters.storekeeper = session_user

	# 6. Resolve allowed users (Stock Users)
	storekeepers = frappe.db.sql_list(
		"""
		SELECT DISTINCT u.name
		FROM `tabUser` u
		INNER JOIN `tabHas Role` r ON r.parent = u.name
		WHERE r.role = %(role)s AND u.enabled = 1
		""",
		{"role": STOREKEEPER_ROLE},
	)

	# Also include users with submitted evaluations in the period (Spec 6.2 step 5)
	evaluated_users = frappe.db.sql_list(
		"""
		SELECT DISTINCT storekeeper
		FROM `tabWarehouse Staff Evaluation`
		WHERE docstatus = 1
			AND from_date <= %(to_date)s
			AND to_date >= %(from_date)s
		""",
		{"from_date": filters.from_date, "to_date": filters.to_date},
	)

	allowed_users = list(set(storekeepers + evaluated_users))
	if own_view:
		allowed_users = [session_user]

	return {
		"filters": filters,
		"is_system_manager": is_system_manager,
		"is_warehouse_manager": is_warehouse_manager,
		"is_storekeeper": is_storekeeper,
		"own_view": own_view,
		"allowed_warehouses": allowed_warehouses,
		"allowed_users": allowed_users,
	}


def get_evaluation_permission_query_conditions(user=None):
	"""
	Database-level query conditions for Warehouse Staff Evaluation (Spec 7.2, 7.3).
	"""
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)
	if "System Manager" in roles:
		return ""

	if MANAGER_ROLE in roles:
		settings = frappe.get_single("Warehouse Staff Evaluation Settings")
		if getattr(settings, "restrict_manager_by_warehouse", 1):
			user_wh = frappe.permissions.get_user_permissions(user).get("Warehouse", [])
			allowed = [p.get("doc") for p in user_wh if p.get("doc")]
			if allowed:
				allowed_str = ", ".join(frappe.db.escape(w) for w in allowed)
				return f"`tabWarehouse Staff Evaluation`.warehouse IN ({allowed_str})"
		return ""

	if STOREKEEPER_ROLE in roles:
		return (
			f"`tabWarehouse Staff Evaluation`.storekeeper = {frappe.db.escape(user)} "
			f"AND `tabWarehouse Staff Evaluation`.docstatus = 1"
		)

	return "1=0"


def has_evaluation_permission(doc, ptype="read", user=None):
	"""
	Record-level permission validation for Warehouse Staff Evaluation (Spec 7.2, 7.3).
	"""
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)
	if "System Manager" in roles:
		return True

	if MANAGER_ROLE in roles:
		settings = frappe.get_single("Warehouse Staff Evaluation Settings")
		if getattr(settings, "restrict_manager_by_warehouse", 1):
			user_wh = frappe.permissions.get_user_permissions(user).get("Warehouse", [])
			allowed = [p.get("doc") for p in user_wh if p.get("doc")]
			if allowed and doc.warehouse not in allowed:
				return False
		return True

	if STOREKEEPER_ROLE in roles:
		if ptype == "read" and doc.storekeeper == user and doc.docstatus == 1:
			return True
		return False

	return False
