import frappe

from mkan_customization.mkan_customization.doctype.po_amendment_log.amendment_reasons import REASON_MAP


def _ensure(reason, amendment_type):
	if frappe.db.exists("Amendment Reason Category", reason):
		doc = frappe.get_doc("Amendment Reason Category", reason)
	else:
		doc = frappe.new_doc("Amendment Reason Category")
		doc.amendment_reason_category = reason
	if amendment_type not in [r.amendment_type for r in doc.get("amendment_types")]:
		doc.append("amendment_types", {"amendment_type": amendment_type})
		doc.flags.ignore_permissions = True
		doc.save()


def execute():
	"""1) move each existing record's single Amendment Type into the new table, 2) add the agreed Type -> Reason pairs.
	Idempotent: records you already created are kept and only missing pairs are added."""
	for d in frappe.db.sql("select name, amendment_type from `tabAmendment Reason Category`", as_dict=True):
		if d.amendment_type:
			_ensure(d.name, d.amendment_type)
	for amendment_type, reasons in REASON_MAP.items():
		for reason in reasons:
			_ensure(reason, amendment_type)
