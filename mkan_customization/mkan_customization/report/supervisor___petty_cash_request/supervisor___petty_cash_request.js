// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Supervisor - Petty Cash Request"] = {
    "filters": [
        {
            "fieldname": "duration",
            "label": __("Duration"),
            "fieldtype": "Select",
            "options": ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"],
            "default": "Daily",
            "reqd": 1,
            "on_change": function() {
                // Refresh the report when duration changes
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "supervisor",
            "label": __("Supervisor"),
            "fieldtype": "Link",
            "options": "User",
        },
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname == "amount" && data && data.amount) {
            value = "<span style='color:" + (data.amount < 0 ? "#FF5858" : "#5e64ff") + ";'>" + value + "</span>";
        }
        
        return value;
    },
    "after_datatable_render": function(datatable_obj) {
        // Adjust chart height based on data
        $(frappe.query_report.wrapper).find('.chart-container').css('height', '300px');
    },
    // Custom tooltip for the chart (applied in JS, not Python)
    "onload": function(report) {
        report.page.add_inner_button(__("Refresh Chart"), function() {
            report.refresh();
        });
        
        // Apply custom tooltip after chart is rendered
        setTimeout(function() {
            if (report.chart && report.chart.tooltip) {
                report.chart.tooltip.formatTooltipY = function(value) {
                    return value + " Petty Cash Requests";
                };
            }
        }, 1000);
    },
    "initial_depth": 0,
    "tree": false,
    "is_tree": false
};