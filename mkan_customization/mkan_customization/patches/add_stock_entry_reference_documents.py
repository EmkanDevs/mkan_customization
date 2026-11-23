import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

from mkan_customization.mkan_customization.doc_events.stock_entry import get_reference_documents

FIELD = {
	"fieldname": "custom_reference_documents",
	"label": "Reference Documents",
	"fieldtype": "Small Text",
	"insert_after": "custom_material_request_references",
	"read_only": 1,
	"no_copy": 1,
	"translatable": 0,
	"module": "Mkan Customization",
	"description": "Unique documents referenced on this Stock Entry and its Items.",
}


def execute():
	# Patches run before fixtures sync, so make sure the field exists first.
	create_custom_field("Stock Entry", FIELD)
	frappe.clear_cache(doctype="Stock Entry")

	for name in frappe.get_all("Stock Entry", pluck="name"):
		doc = frappe.get_doc("Stock Entry", name)
		references = get_reference_documents(doc)
		if (doc.get("custom_reference_documents") or "") != references:
			doc.db_set("custom_reference_documents", references, update_modified=False)
