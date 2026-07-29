import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def bid_tabulation(source_name, target_doc=None):

	def set_parent_wbs(source, target):
		# 🔥 Set first custom_wbs from RFQ items to parent wbs field
		for row in source.items:
			if row.custom_wbs:
				target.wbs = row.custom_wbs
				break  # take first and stop

	doc = get_mapped_doc(
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
		postprocess=set_parent_wbs
	)

	return doc


# 🔥 Supplier validation on submit
def on_submit(self, method):
	if len(self.suppliers) < 3:
		frappe.throw(_("At least 3 suppliers are required to submit the Request for Quotation."))
