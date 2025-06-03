// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Site Violation Charges', {
    refresh: function(frm) {
        // Add the custom button on the form
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Create Payment Entries'), function () {
                // Call the server-side function to create Payment Entries
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.site_violation_charges.site_violation_charges.create_payment_entries_for_violation",
                    args: {
                        docname: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(__('Payment Entries created successfully.'));
                        }
                    }
                });
            });
        }
    },
});
