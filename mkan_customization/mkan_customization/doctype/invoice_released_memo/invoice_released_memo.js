// // Copyright (c) 2025, Finbyz and contributors
// // For license information, please see license.txt


frappe.ui.form.on('Invoice released Memo', {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button('Connect', () => {
            if (!(frm.doc.project_no && frm.doc.vendor && frm.doc.project_sub_contracts)) {
                frappe.msgprint(__('Please set Project No, Vendor, and Project Sub-Contracts before connecting.'));
                return;
            }

            const dialog = new frappe.ui.Dialog({
                title: 'Connect Work Progress Report',
                fields: [
                    {
                        label: 'Work Progress Report',
                        fieldname: 'work_progress_report',
                        fieldtype: 'Link',
                        options: 'Work Progress Report',
                        reqd: 1,
                        get_query: () => {
                            return {
                                query: 'mkan_customization.mkan_customization.doctype.invoice_released_memo.invoice_released_memo.get_matching_work_progress_reports',
                                filters: {
                                    project_no: frm.doc.project_no,
                                    vendor: frm.doc.vendor,
                                    project_sub_contracts: frm.doc.project_sub_contracts
                                }
                            };
                        }
                    }
                ],
                primary_action_label: 'Connect',
                primary_action(values) {
                   frappe.call({
                        method: "mkan_customization.mkan_customization.doctype.invoice_released_memo.invoice_released_memo.set_work_progress_report",
                        args: {
                            invoice_name: frm.doc.name,
                            work_progress_report: values.work_progress_report
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.msgprint(r.message || "Linked successfully.");
                                // frm.reload_doc(); // Refresh the form to show updated field
                                dialog.hide();
                            }
                        }
                    });

                    // frm.set_value('work_progress_report', values.work_progress_report);
                    // dialog.hide();
                }
            });

            dialog.show();
        });
        }
        
    },
});

frappe.ui.form.on('Invoice Released Memo Detail', {
    contract__quantity: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_values(row);
        frm.refresh_field('invoice_released_memo_detail');
    },
    unit_rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_values(row);
        frm.refresh_field('invoice_released_memo_detail');
    },
    current_quantity: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_values(row);
        frm.refresh_field('invoice_released_memo_detail');
    },
    previous_quantity: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_values(row);
        frm.refresh_field('invoice_released_memo_detail');
    }
});


function calculate_row_values(row) {
    if (row.contract__quantity && row.unit_rate) {
        frappe.model.set_value(row.doctype, row.name, 'contract_price', row.contract__quantity * row.unit_rate);
    }
    if (row.current_quantity && row.previous_quantity) {
        frappe.model.set_value(row.doctype, row.name, 'accumulate_quantity', row.current_quantity + row.previous_quantity);
    }
}





