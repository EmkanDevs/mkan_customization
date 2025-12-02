// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payment Requester", {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Payment Entry'), function() {
                // create new Payment Entry
                let pe = frappe.model.get_new_doc("Payment Entry");

                // map values from Payment Requester
                pe.party_type = frm.doc.party_type;
                pe.party = frm.doc.party;
                pe.party_name = frm.doc.party_name;
                pe.received_amount = frm.doc.amount;
                pe.payment_type = frm.doc.payment_type || "Pay";
                if (pe.payment_type === "Pay") {
                    pe.paid_amount = frm.doc.grand_total;
                } else if (pe.payment_type === "Receive") {
                    pe.received_amount = frm.doc.grand_total;
                }
                pe.posting_date = frm.doc.transaction_date
                pe.mode_of_payment = frm.doc.mode_of_payment
                pe.custom_payment_reference_doctype = 'Payment Requester'
                pe.custom_payment_reference_name = frm.doc.name

                // add reference row
                if (frm.doc.reference_doctype && frm.doc.reference_name) {
                    frappe.model.add_child(pe, "Payment Entry Reference", "references", {
                        reference_doctype: frm.doc.reference_doctype,
                        reference_name: frm.doc.reference_name,
                        total_amount: frm.doc.amount,
                        outstanding_amount: frm.doc.amount,
                        allocated_amount: frm.doc.amount
                    });
                }

                // route to the new Payment Entry form
                frappe.set_route("Form", pe.doctype, pe.name);
            }, __("Create"));
        }
    }
});

