	// Copyright (c) 2025, Finbyz and contributors
	// For license information, please see license.txt

	frappe.query_reports["MR Details"] = {
		"filters": [
			{
				"fieldname": "id",
				"label": __("ID"),
				"fieldtype": "MultiSelectList",
				"options": "Material Request",
				"get_data": function(txt) {
					return frappe.db.get_link_options("Material Request", txt);
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
