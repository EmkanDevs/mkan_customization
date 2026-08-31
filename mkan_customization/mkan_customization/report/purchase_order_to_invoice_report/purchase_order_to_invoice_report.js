// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Order to Invoice Report"] = {
	filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
        },
		{
            fieldname: "purchase_order",
            label: __("Purchase Order Reference"),
            fieldtype: "Link",
            options: "Purchase Receipt",
        },
        {
            fieldname: "purchase_receipt",
            label: __("Purchase Receipt Reference"),
            fieldtype: "Link",
            options: "Purchase Receipt",
        },
		{
            fieldname: "purchase_invoice",
            label: __("Purchase Invoice Reference"),
            fieldtype: "Link",
            options: "Purchase Invoice",
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier",
        },
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project",
        },
    ],
};
