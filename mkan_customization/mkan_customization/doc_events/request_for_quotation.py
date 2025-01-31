import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def bid_tabulation(source_name, target_doc=None):

	doclist = get_mapped_doc(
		"Request for Quotation",
		source_name,
		{
			"Request for Quotation": {
				"doctype": "Bid Tabulation Discussion",
				"validation": {
					"docstatus": ["=", 1],
				},
			},
		},
		target_doc,
	)

	return doclist