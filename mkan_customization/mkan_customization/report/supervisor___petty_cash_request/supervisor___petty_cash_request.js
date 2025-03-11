// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Supervisor - Petty Cash Request"] = {
    "filters": [
        {
            "fieldname": "duration",
            "label": __("Duration"),
            "fieldtype": "Select",
            "options": ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"],
            "default": "Monthly",
            "reqd": 1,
            "on_change": function() {
                frappe.query_report.refresh();
            }
        },
        {
            "fieldname": "supervisor",
            "label": __("Supervisor"),
            "fieldtype": "Link",
            "options": "User",
            "default": frappe.session.user,
            "get_query": function() {
                if (frappe.user.has_role("System Manager")) {
                    return {}; // No filter applied
                }
                return {
                    filters: {
                        name: ["in", cur_supervisors]
                    }
                };
            }
        }
    ],

    "onload": function(report) {
       
            frappe.call({
                method: "mkan_customization.mkan_customization.report.supervisor___petty_cash_request.supervisor___petty_cash_request.get_petty_cash_requests",
                callback: function(r) {
                    cur_supervisors = r.message || [];

                    // Ensure the logged-in user is always in the list
                    if (!cur_supervisors.includes(frappe.session.user)) {
                        cur_supervisors.unshift(frappe.session.user);
                    }

                    // Set the default supervisor filter
                    frappe.query_report.set_filter_value("supervisor", frappe.session.user);
                }
            });
        

        report.page.add_inner_button(__("Refresh Chart"), function() {
            report.refresh();
        });

        setTimeout(function() {
            if (report.chart && report.chart.tooltip) {
                report.chart.tooltip.formatTooltipY = function(value) {
                    return value + " Petty Cash Requests";
                };
            }
        }, 1000);
    },

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "amount" && data && data.amount) {
            value = "<span style='color:" + (data.amount < 0 ? "#FF5858" : "#5e64ff") + ";'>" + value + "</span>";
        }

        return value;
    },

    "after_datatable_render": function(datatable_obj) {
        $(frappe.query_report.wrapper).find('.chart-container').css('height', '300px');
    },

    "initial_depth": 0,
    "tree": false,
    "is_tree": false
};