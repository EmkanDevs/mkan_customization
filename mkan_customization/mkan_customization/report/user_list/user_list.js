// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["User List"] = {
	"filters": [
		{
			"fieldname": "user",
			"label": __("User"),
			"fieldtype": "Link",
			"options": "User",

		},
		{
			"fieldname": "role",
			"label": __("Role"),
			"fieldtype": "Link",
			"options": "Role",
		},
	]
};
