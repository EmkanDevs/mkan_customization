frappe.ui.form.on('Sales Order', {
    retention(frm) {
        calculate_retention(frm);
    },
    validate(frm) {
        calculate_retention(frm);  // Recalculate on submit/validate too
    },
    total(frm) {
        calculate_retention(frm);  // In case total is updated from backend
    },
    refresh(frm) {
        frm.add_custom_button('Advance Payment Report', function() {
            frappe.set_route('query-report', 'Advance Payment',{"sales_order":frm.doc.name});
        },"Report");
        
        frm.add_custom_button('Retention Report', function() {
            frappe.set_route('query-report', 'Retention Report',{"sales_order":frm.doc.name});
        },"Report");
    }
});

function calculate_retention(frm) {
    const total = frm.doc.total || 0;
    const retention_percent = frm.doc.retention || 0;
    const retention_amount = (total * retention_percent) / 100;
    frm.set_value('retention_amount', retention_amount);
}