// Copyright (c) 2025, Finbyz and contributors

frappe.ui.form.on("Temp Room Booking", {
    refresh(frm) {
        if (frm.is_new()) return;

        frm.add_custom_button(__('Create Payment Request'), () => {
            frappe.call({
                method: "mkan_customization.mkan_customization.doctype.temp_room_booking.temp_room_booking.make_trb_payment_request",
                args: { docname: frm.doc.name },
                callback(r) {
                    if (r.message) {
                        frappe.model.sync(r.message);
                        frappe.set_route("Form", "Payment Requester", r.message.name);
                    }
                }
            });
        }, __("Create"));

        frappe.db.get_value("Payment Requester", {
            reference_doctype: frm.doctype,
            reference_name: frm.doc.name
        }, "name").then(r => {
            if (r?.message?.name) {
                frm.add_custom_button(__('Create Purchase Invoice'), () => {
                    create_trb_purchase_invoice(frm, r.message.name);
                }, __("Create"));
            }
        });
    }
});

function create_trb_purchase_invoice(frm, payment_requester) {
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
        bill_no : frm.doc.invoice_no,
        bill_date : frm.doc.invoice_date,
        reference_doctype_payment: "Payment Requester",
        ref_payment_name: payment_requester,
        reference_doctype: frm.doctype,
        reference_name: frm.doc.name,

    });
}
