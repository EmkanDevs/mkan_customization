// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["PO Details"] = {
	"filters": [
			{
				"fieldname": "id",
				"label": __("ID"),
				"fieldtype": "MultiSelectList",
				"options": "Purchase Order",
				"get_data": function(txt) {
					return frappe.db.get_link_options("Purchase Order", txt);
				}
			},
			{
				"fieldname": "project",
				"label": __("Project"),
				"fieldtype": "MultiSelectList",
				"options": "Project",
				"get_data": function(txt) {
					return frappe.db.get_link_options("Project", txt);
				}
			},
		]
};
