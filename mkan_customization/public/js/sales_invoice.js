frappe.ui.form.on('Sales Invoice', {
    retention(frm) {
        calculate_retention(frm);
    },
    sales_order(frm) {
        fetch_retention_from_sales_order(frm);
    },
    total(frm) {
        calculate_retention(frm);
        calculate_advance_amount(frm);
    },
    validate(frm) {
        calculate_retention(frm);
        // calculate_advance_amount(frm);
    },
    onload(frm) {
        if (frm.doc.sales_order && !frm.doc.__islocal) {
            fetch_retention_from_sales_order(frm);
            // add_manual_advance_row(frm);
            // calculate_advance_amount(frm);
            calculate_retention(frm);
        }
    },
    advance_payment(frm) {
        // add_manual_advance_row(frm);
    },
 
});

function calculate_retention(frm) {
    const total = frm.doc.total || 0;
    const retention_percent = frm.doc.retention || 0;
    const retention_amount = (total * retention_percent) / 100;
    // rention_amount
    if (!frm.doc.retention_amount){
        frm.set_value('retention_amount', retention_amount);
    }
}


function fetch_retention_from_sales_order(frm) {
    if (!frm.doc.sales_order) return;

    frappe.db.get_doc('Sales Order', frm.doc.sales_order).then(sales_order => {
        const retention = sales_order.retention || 0;
        const advance_payment = sales_order.advance_payment || 0;

        frm.set_value('retention', retention);
    });
}

function add_manual_advance_row(frm) {
    const total = frm.doc.total || 0;
    const advance_percent = frm.doc.advance_payment || 0;
    const advance_amount = (total * advance_percent) / 100;

    // Optional: clear old manually added rows
    frm.clear_table("advances");

    // Add custom row to advances table
    const row = frm.add_child("advances");
    // row.reference_type = "Manual"; // or "Payment Entry" if needed
    row.reference_name = ""; // Leave empty
    row.allocated_amount = advance_amount;
    row.difference_posting_date = frappe.datetime.get_today();

    // frm.set_value("advance_amount", advance_amount);
    frm.refresh_field("advances");
}


frappe.ui.form.on('Sales Invoice Item', {
    uom: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code || !row.uom) return;

        frappe.call({
            method: 'frappe.client.get',
            args: { doctype: 'Item', name: row.item_code },
            callback: function(r) {
                if (!r.message) return;
                let valid_uoms = (r.message.uoms || []).map(u => u.uom);
                if (!valid_uoms.includes(row.uom)) {
                    frappe.msgprint({
                        title: __('Invalid UOM'),
                        message: __(`UOM <b>${row.uom}</b> is not valid for item <b>${row.item_code}</b>.<br>Valid UOM(s): <b>${valid_uoms.join(', ')}</b>`),
                        indicator: 'red'
                    });
                    frappe.model.set_value(cdt, cdn, 'uom', '');
                    frm.refresh_field('items');
                }
            }
        });
    }
});