import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# Standard ERPNext and HRMS fields that mkan_customization filters or joins on.
# An index only makes lookups faster, the rows returned stay exactly the same.
# Custom fields and the app's own doctypes get their index through
# "search_index": 1 in the fixtures and doctype JSON instead.
STANDARD_FIELDS_TO_INDEX = (
	("Stock Entry", "outgoing_stock_entry"),
	("Request for Quotation Item", "material_request"),
	("Supplier Quotation Item", "request_for_quotation"),
	("Employee Advance", "employee"),
)


def execute():
	for doctype, fieldname in STANDARD_FIELDS_TO_INDEX:
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		df = meta.get_field(fieldname)
		if not df or df.search_index:
			continue

		# A property setter, not a bare ALTER TABLE: Frappe's schema sync reads
		# search_index from the meta, so it keeps this index on later migrations
		# instead of dropping it. If the column already has an index under any
		# name, the sync sees it and does not add a second one.
		make_property_setter(
			doctype,
			fieldname,
			"search_index",
			1,
			"Check",
			validate_fields_for_doctype=False,
		)
		frappe.db.updatedb(doctype)
