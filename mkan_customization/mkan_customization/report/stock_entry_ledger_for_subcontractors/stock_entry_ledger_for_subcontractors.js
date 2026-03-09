// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Entry Ledger for Subcontractors"] = {
	 "filters": [

        {
            fieldname: "project",
            label: "Project",
            fieldtype: "Link",
            options: "Project"
        },

        {
            fieldname: "supplier",
            label: "Supplier",
            fieldtype: "Link",
            options: "Supplier"
        },

        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date"
        },

        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date"
        }

    ]
};
