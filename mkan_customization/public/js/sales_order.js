frappe.ui.form.on('Sales Order', {
    retention(frm) {
        calculate_so_amounts(frm);
    },
    advance_payment(frm) {
        calculate_so_amounts(frm);
    },
    validate(frm) {
        calculate_so_amounts(frm);
    },
    total(frm) {
        calculate_so_amounts(frm);
    },
    refresh(frm) {
        frm.add_custom_button(__('Advance Payment Report'), function() {
            frappe.set_route('query-report', 'Advance Payment', {"sales_order": frm.doc.name});
        }, __('Report'));
        
        frm.add_custom_button(__('Retention Report'), function() {
            frappe.set_route('query-report', 'Retention Report', {"sales_order": frm.doc.name});
        }, __('Report'));
    }
});

function calculate_so_amounts(frm) {
    const total = flt(frm.doc.net_total || frm.doc.total || 0);

    const retention_percent = flt(frm.doc.retention || 0);
    const retention_amount = (total * retention_percent) / 100;
    if (frm.fields_dict['custom_retention_amount']) {
        frm.set_value('custom_retention_amount', retention_amount);
    }
    if (frm.fields_dict['retention_amount']) {
        frm.set_value('retention_amount', retention_amount);
    }

    const advance_percent = flt(frm.doc.advance_payment || 0);
    const advance_amount = (total * advance_percent) / 100;
    if (frm.fields_dict['custom_advance_amount']) {
        frm.set_value('custom_advance_amount', advance_amount);
    }
}