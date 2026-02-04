// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Returned Material to Warehouse Request', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Stock Entry'), function () {
                create_stock_entry_from_rmwr(frm);
            });
        }
    }
});


function create_stock_entry_from_rmwr(frm) {
    frappe.model.open_mapped_doc({
        method: 'mkan_customization.mkan_customization.doctype.returned_material_to_warehouse_request.returned_material_to_warehouse_request.create_stock_entry_from_rmwr',
        frm: frm,
        args: {
            rmwr_name: frm.doc.name
        }
    });
}