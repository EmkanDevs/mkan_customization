// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Advance Payment"] = {
	"filters": [
		{
			"fieldname": "sales_order",
			"label": "Sales Order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"reqd": 1
		}
	]
};
