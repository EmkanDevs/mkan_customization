// Copyright (c) 2025, Finbyz and contributors

frappe.ui.form.on('Project Site Violation', {
    onload(frm) {
        let account_filter = {
            filters: {
                company: 'Construction Pillars Company',
                is_group: 0,
                account_currency: 'SAR'
            }
        };

        frm.set_query('from_account', () => account_filter);
        frm.set_query('to_account', () => account_filter);
    },

    refresh(frm) {
        if (frm.is_new()) return;

        // Payment Requester
        frm.add_custom_button(__('Create Payment Request'), () => {
            frappe.call({
                method: "mkan_customization.mkan_customization.doctype.project_site_violation.project_site_violation.make_payment_request",
                args: { docname: frm.doc.name },
                callback(r) {
                    if (r.message) {
                        frappe.model.sync(r.message);
                        frappe.set_route("Form", "Payment Requester", r.message.name);
                    }
                }
            });
        }, __("Create"));

        // Show PI only after Payment Requester exists
        frappe.db.get_value("Payment Requester", {
            reference_doctype: frm.doctype,
            reference_name: frm.doc.name
        }, "name").then(r => {
            if (r?.message?.name) {
                frm.add_custom_button(__('Create Purchase Invoice'), () => {
                    create_psv_purchase_invoice(frm, r.message.name);
                }, __("Create"));
            }
        });

        // Journal Entry (existing)
        frm.add_custom_button(__('Create Journal Entry'), () => {
            if (!frm.doc.from_account || !frm.doc.to_account) {
                frappe.msgprint(__('Please set both From Account and To Account'));
                return;
            }

            frappe.call({
                method: 'frappe.client.insert',
                args: {
                    doc: {
                        doctype: 'Journal Entry',
                        posting_date: frappe.datetime.now_date(),
                        project_site_violation: frm.doc.name,
                        company: frm.doc.company,
                        cheque_no: frm.doc.sadad_no,
                        cheque_date: frm.doc.payment_due_date,
                        accounts: [
                            { account: frm.doc.from_account, debit_in_account_currency: frm.doc.penalty_amount },
                            { account: frm.doc.to_account, credit_in_account_currency: frm.doc.penalty_amount }
                        ],
                        user_remark: `Auto-created from Project Site Violation: ${frm.doc.name}`
                    }
                },
                callback(r) {
                    if (r.message) {
                        frappe.set_route('Form', 'Journal Entry', r.message.name);
                    }
                }
            });
        });
    }
});

function create_psv_purchase_invoice(frm, payment_requester) {
    frappe.new_doc('Purchase Invoice', {
        project: frm.doc.project,
        supplier: frm.doc.payment_to,
        due_date: frm.doc.payment_due_date,
        sector: frm.doc.sector,
        scope : frm.doc.scope,
        department : frm.doc.department,
        section : frm.doc.section,
        region_location : frm.doc.region_location,
        cost_center: frm.doc.cost_center,
        reference_doctype_payment: "Payment Requester",
        ref_payment_name: frm.doc.payment_requester,
        reference_doctype: frm.doctype,
        reference_name: frm.doc.name,

    });
}
