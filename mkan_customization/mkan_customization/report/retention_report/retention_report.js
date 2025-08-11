// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Retention Report"] = {
    "filters": [
        {
            "fieldname": "sales_order",
            "label": __("Sales Order"),
            "fieldtype": "Link",
            "options": "Sales Order",
			"reqd": 1
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        if (column.fieldname === "retention_amount" && data.retention_amount > 0) {
            value = `<span style="color: red; font-weight: bold;">${value}</span>`;
        }

        if (column.fieldname === "retention_percentage" && data.retention_percentage > 10) {
            value = `<span style="color: red; font-weight: bold;">${value}</span>`;
        }

        return value;
    }
};
