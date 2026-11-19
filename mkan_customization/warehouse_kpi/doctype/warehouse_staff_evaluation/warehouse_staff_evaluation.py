import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from mkan_customization.warehouse_kpi.scope import STOREKEEPER_ROLE


class WarehouseStaffEvaluation(Document):
	def before_insert(self):
		self.evaluated_by = frappe.session.user
		# The form may send one empty row, so check for questions, not for rows.
		if not any(r.question for r in self.ratings):
			self.populate_questions_snapshot()

	def validate(self):
		self.set_title()
		self.validate_dates()
		self.validate_storekeeper_role()
		self.validate_warehouse()
		self.validate_no_overlap()
		self.calculate_score()

	def on_submit(self):
		self.validate_ratings_on_submit()

	def set_title(self):
		display_name = self.storekeeper_name or self.storekeeper
		self.title = f"{display_name}, {self.from_date} to {self.to_date}"

	def validate_dates(self):
		if not self.from_date or not self.to_date:
			frappe.throw(_("From Date and To Date are mandatory."))
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be after To Date."))

	def validate_storekeeper_role(self):
		has_role = frappe.db.exists(
			"Has Role",
			{"parent": self.storekeeper, "role": STOREKEEPER_ROLE},
		)
		if not has_role:
			frappe.throw(
				_("Selected user {0} does not have the '{1}' role.").format(
					frappe.bold(self.storekeeper), STOREKEEPER_ROLE
				)
			)

	def validate_warehouse(self):
		is_group = frappe.db.get_value("Warehouse", self.warehouse, "is_group")
		if is_group:
			frappe.throw(_("Evaluation cannot be created for a group warehouse ({0}).").format(frappe.bold(self.warehouse)))

		# Verify permission if restricted manager
		if "System Manager" not in frappe.get_roles():
			settings = frappe.get_single("Warehouse Staff Evaluation Settings")
			if getattr(settings, "restrict_manager_by_warehouse", 1):
				user_warehouses = frappe.permissions.get_user_permissions(frappe.session.user).get("Warehouse", [])
				allowed_warehouses = [p.get("doc") for p in user_warehouses if p.get("doc")]
				if allowed_warehouses and self.warehouse not in allowed_warehouses:
					frappe.throw(
						_("You are not authorized to evaluate staff for warehouse {0}.").format(
							frappe.bold(self.warehouse)
						),
						frappe.PermissionError,
					)

	def validate_no_overlap(self):
		"""
		Ensure no other non-cancelled evaluation exists for the same storekeeper and warehouse
		with overlapping dates (from_date <= other.to_date and to_date >= other.from_date).
		"""
		filters = {
			"docstatus": ["!=", 2],
			"storekeeper": self.storekeeper,
			"warehouse": self.warehouse,
			"from_date": ["<=", self.to_date],
			"to_date": [">=", self.from_date],
		}

		if not self.is_new():
			filters["name"] = ["!=", self.name]

		if self.amended_from:
			filters["name"] = ["not in", [self.name, self.amended_from]]

		overlapping = frappe.db.get_value(
			"Warehouse Staff Evaluation",
			filters,
			["name", "from_date", "to_date"],
			as_dict=True,
		)

		if overlapping:
			frappe.throw(
				_(
					"An evaluation {0} already exists for storekeeper {1} in warehouse {2} "
					"for period {3} to {4} which overlaps with this date range."
				).format(
					frappe.bold(overlapping.name),
					frappe.bold(self.storekeeper),
					frappe.bold(self.warehouse),
					overlapping.from_date,
					overlapping.to_date,
				)
			)

	def populate_questions_snapshot(self):
		"""Copy active questions from Settings as a snapshot into child table."""
		settings = frappe.get_single("Warehouse Staff Evaluation Settings")
		if not settings.questions:
			settings.populate_default_questions()

		active_questions = [q.question for q in settings.questions if q.is_active]
		self.set("ratings", [])
		for q in active_questions:
			self.append("ratings", {"question": q, "rating": None, "remarks": ""})

	def calculate_score(self):
		"""Calculate overall score and score percentage on server side."""
		valid_ratings = [
			flt(r.rating)
			for r in self.ratings
			if r.rating and str(r.rating).strip() in ["1", "2", "3", "4", "5"]
		]

		if valid_ratings:
			self.overall_score = round(sum(valid_ratings) / len(valid_ratings), 2)
			self.score_percent = round((self.overall_score / 5.0) * 100, 2)
		else:
			self.overall_score = 0.0
			self.score_percent = 0.0

	def validate_ratings_on_submit(self):
		"""On submit, every rating question must be answered between 1 and 5."""
		if not self.ratings:
			frappe.throw(_("At least one evaluation question rating is required before submission."))

		for idx, row in enumerate(self.ratings, start=1):
			if not row.rating or str(row.rating).strip() not in ["1", "2", "3", "4", "5"]:
				frappe.throw(
					_("Row #{0}: Please provide a rating between 1 and 5 for '{1}' before submitting.").format(
						idx, row.question
					)
				)


@frappe.whitelist()
def get_active_questions():
	"""Active questions for a new evaluation. A new form never runs the server onload, so the client asks."""
	settings = frappe.get_single("Warehouse Staff Evaluation Settings")
	if not settings.questions:
		settings.populate_default_questions()
	return [q.question for q in settings.questions if q.is_active]
