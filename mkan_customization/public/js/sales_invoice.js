frappe.ui.form.on('Sales Invoice', {
    setup(frm) {
        set_income_account_query(frm);
    },
    onload(frm) {
        set_income_account_query(frm);
    },
    refresh(frm) {
        set_income_account_query(frm);
    },
    retention(frm) {
        validate_and_calculate(frm);
    },
    advance_payment(frm) {
        validate_and_calculate(frm);
    },
    total(frm) {
        calculate_cpc_billing(frm);
    },
    net_total(frm) {
        calculate_cpc_billing(frm);
    },
    grand_total(frm) {
        calculate_cpc_billing(frm);
    },
    validate(frm) {
        // F01: Range validation
        if (frm.doc.advance_payment !== undefined && frm.doc.advance_payment !== null && frm.doc.advance_payment !== "") {
            const adv = flt(frm.doc.advance_payment);
            if (adv < 0 || adv > 100) {
                frappe.msgprint(__('Advance Recovery % must be between 0 and 100.'));
                frappe.validated = false;
                return false;
            }
        }
        if (frm.doc.retention !== undefined && frm.doc.retention !== null && frm.doc.retention !== "") {
            const ret = flt(frm.doc.retention);
            if (ret < 0 || ret > 100) {
                frappe.msgprint(__('Retention % must be between 0 and 100.'));
                frappe.validated = false;
                return false;
            }
        }
        calculate_cpc_billing(frm);
    }
});

// Replaces ERPNext's default income_account query (Income root type only)
// on the Items table.
function set_income_account_query(frm) {
    frm.set_query('income_account', 'items', function (doc) {
        return {
            filters: {
                root_type: ['!=', 'Expense'],
                disabled: 0,
                is_group: 0,
                company: doc.company
            }
        };
    });
}

function validate_and_calculate(frm) {
    if (frm.doc.advance_payment !== undefined && frm.doc.advance_payment !== null && frm.doc.advance_payment !== "") {
        const adv = flt(frm.doc.advance_payment);
        if (adv < 0 || adv > 100) {
            frappe.show_alert({
                message: __('Advance Recovery % must be between 0 and 100.'),
                indicator: 'red'
            });
            return;
        }
    }
    if (frm.doc.retention !== undefined && frm.doc.retention !== null && frm.doc.retention !== "") {
        const ret = flt(frm.doc.retention);
        if (ret < 0 || ret > 100) {
            frappe.show_alert({
                message: __('Retention % must be between 0 and 100.'),
                indicator: 'red'
            });
            return;
        }
    }
    calculate_cpc_billing(frm);
}

function calculate_cpc_billing(frm) {
    if (frm.doc.docstatus === 1) return;

    const net_total = flt(frm.doc.net_total || frm.doc.total || 0);

    // 1. Calculate Retention Amount strictly based on THIS invoice's net total
    const retention_percent = flt(frm.doc.retention || 0);
    const retention_amount = flt((net_total * retention_percent) / 100, 2);
    frm.set_value('retention_amount', retention_amount);

    // 2. Adjust Advance Allocation if advances rows exist
    const recovery_percent = flt(frm.doc.advance_payment || 0);
    const target_recovery = flt((net_total * recovery_percent) / 100, 2);

    let total_advance = 0;
    let remaining_recovery = target_recovery;

    if (frm.doc.advances && frm.doc.advances.length) {
        frm.doc.advances.forEach(row => {
            const available = flt(row.advance_amount);
            if (remaining_recovery > 0) {
                const alloc = Math.min(remaining_recovery, available);
                row.allocated_amount = alloc;
                remaining_recovery -= alloc;
            } else {
                row.allocated_amount = 0;
            }
            total_advance += flt(row.allocated_amount);
        });
        frm.refresh_field('advances');
        frm.set_value('total_advance', total_advance);
    } else {
        total_advance = flt(frm.doc.total_advance || 0);
    }

    // 3. Calculate Custom Outstanding Value (Amount Due Now)
    const grand_total = flt(frm.doc.rounded_total || frm.doc.grand_total || 0);
    const current_due = Math.max(0, grand_total - total_advance - retention_amount);
    frm.set_value('custom_outstanding_value_', current_due);
}


