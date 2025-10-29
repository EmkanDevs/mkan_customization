// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Warehouse Receipt wise Item Expiration"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "warehouse",
			"label": "Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname": "item",
			"label": "Item",
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "item_group",
			"label": "Item Group",
			"fieldtype": "Link",
			"options": "Item Group"
		},
		{
			"fieldname": "days_till_expire",
			"label": "Days Till Expire",
			"fieldtype": "Int"
		}
	]
};
