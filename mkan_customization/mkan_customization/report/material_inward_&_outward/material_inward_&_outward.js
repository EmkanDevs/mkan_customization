// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Material Inward & Outward"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "warehouse",
			"label": "Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse"
		}
	]
};
