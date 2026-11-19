import frappe
from frappe.model.document import Document


DEFAULT_QUESTIONS = [
	"Warehouse organization and material arrangement",
	"Proper material identification and labeling",
	"Material preservation and prevention of damage",
	"Compliance with warehouse safety requirements",
]


class WarehouseStaffEvaluationSettings(Document):
	def onload(self):
		if not self.questions:
			self.populate_default_questions()

	def populate_default_questions(self):
		if not self.questions:
			for q in DEFAULT_QUESTIONS:
				self.append("questions", {"question": q, "is_active": 1})


def init_default_settings():
	doc = frappe.get_doc("Warehouse Staff Evaluation Settings")
	if not doc.questions:
		for q in DEFAULT_QUESTIONS:
			doc.append("questions", {"question": q, "is_active": 1})
		doc.save(ignore_permissions=True)
		frappe.db.commit()
