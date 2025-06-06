// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Project Contract Details"] = {
	"filters": [
		{
			"fieldname": "project",
			"label": "Project",
			"fieldtype": "Link",
			"options": "Project",
			"reqd": 0
		},
		{
			"fieldname": "project_sub_contract",
			"label": "Project Sub-contract",
			"fieldtype": "Link",
			"options": "Project Sub-Contracts",
			"reqd": 0
		}
	]
};
