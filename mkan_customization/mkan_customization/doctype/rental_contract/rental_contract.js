frappe.ui.form.on("Rental Contract", {
    refresh(frm) {
        if (frm.is_new()) return;

        // Always show Payment Requester
        frm.add_custom_button(__('Create Payment Request'), () => {
            frappe.call({
                method: "mkan_customization.mkan_customization.doctype.rental_contract.rental_contract.make_payment_request",
                args: { rental_contract: frm.doc.name },
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
                    create_rc_purchase_invoice(frm, r.message.name);
                }, __("Create"));
            }
        });
    }
});

function create_rc_purchase_invoice(frm, payment_requester) {
    frappe.new_doc('Purchase Invoice', {
        project: frm.doc.project,
        due_date: frm.doc.payment_due_date,
        sector: frm.doc.sector,
        scope : frm.doc.scope,
        department : frm.doc.department,
        section : frm.doc.section,
        region_location : frm.doc.location,
        cost_center: frm.doc.cost_center,
        reference_doctype_payment: "Payment Requester",
        ref_payment_name: frm.doc.payment_requester,
        reference_doctype: frm.doctype,
        reference_name: frm.doc.name,
    });
}
