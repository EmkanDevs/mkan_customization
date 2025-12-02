// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Project Permit", {
    valid_from: function(frm) {
        calculate_duration(frm);
    },
    valid_to: function(frm) {
        calculate_duration(frm);
    },
	refresh(frm) {
        frm.add_custom_button(__('Create Payment Request'), function() {
            frappe.call({
                method: "mkan_customization.mkan_customization.doctype.project_permit.project_permit.make_pp_payment_request",
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.sync(r.message);
                        frappe.show_alert({
                            message: __("Payment Request {0} created as Draft", [r.message.name]),
                            indicator: "green"
                        });
                        frappe.set_route("Form", "Payment Requester", r.message.name);
                    }
                }
            });
        }, __("Create"));
	},
});
function calculate_duration(frm) {
    if (frm.doc.valid_from && frm.doc.valid_to) {
        let from_date = frappe.datetime.str_to_obj(frm.doc.valid_from);
        let to_date = frappe.datetime.str_to_obj(frm.doc.valid_to);

        let diff_days = frappe.datetime.get_day_diff(to_date, from_date);

        frm.set_value("permit_duration_days", diff_days);
    }
}

