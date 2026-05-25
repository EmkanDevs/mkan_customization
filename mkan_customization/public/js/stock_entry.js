erpnext.stock.StockEntry = class StockEntry extends erpnext.stock.StockEntry {

    company() {
        if (this.frm.doc.company) {
            var company_doc = frappe.get_doc(":Company", this.frm.doc.company);
            if (company_doc.default_letter_head) {
                this.frm.set_value("letter_head", company_doc.default_letter_head);
            }
            this.frm.trigger("toggle_display_account_head");

            erpnext.accounts.dimensions.update_dimension(this.frm, this.frm.doctype);
            if (this.frm.doc.company && erpnext.is_perpetual_inventory_enabled(this.frm.doc.company))
                this.set_default_account("stock_adjustment_account", "expense_account");
            if (!cost_center) {
                this.set_default_account("cost_center", "cost_center");
            }


            this.frm.refresh_fields("items");
        }
    }
}

extend_cscript(cur_frm.cscript, new erpnext.stock.StockEntry({ frm: cur_frm }));

frappe.ui.form.on("Stock Entry", {
    refresh(frm) {
        // Add button to create Returned Material to Warehouse Request
        // Only show if Stock Entry is submitted and has a project
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Create Returned Material to Warehouse Request"), () => {
                frappe.model.open_mapped_doc({
                    method: "mkan_customization.mkan_customization.override.stock_entry.create_returned_material_to_warehouse_request",
                    frm: frm
                });
            });
        }

        if (frm.doc.stock_entry_type === "Send to Subcontractor" && frm.doc.custom_supplier_code) {

            frm.add_custom_button("View Project Sub-Contracts", () => {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.get_project_sub_contracts_for_stock_entry",
                    args: {
                        supplier: frm.doc.custom_supplier_code,
                        posting_date: frm.doc.posting_date
                    },
                    callback(r) {
                        if (r.message && r.message.length > 0) {
                            show_psc_popup(r.message);
                        } else {
                            frappe.msgprint("No matching Project Sub-contracts found.");
                        }
                    }
                });
            });
        }
    }
});

function show_psc_popup(data) {
    let d = new frappe.ui.Dialog({
        title: "Related Project Sub-Contracts",
        size: "extra-large",
        fields: [
            { fieldname: "html_table", fieldtype: "HTML" }
        ]
    });

    let table_html = `
        <table class="table table-bordered table-hover">
            <thead>
                <tr>
                    <th>PSC Name</th>
                    <th>Supplier</th>
                    <th>Start Date</th>
                    <th>End Date</th>
                    <th>Status</th>
                    <th>Project Name</th>
                    <th>Project Number</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(row => `
                    <tr>
                        <td><a href="/app/project-sub-contract/${row.name}" target="_blank">${row.name}</a></td>
                        <td>${row.party_name}</td>
                        <td>${row.start_date}</td>
                        <td>${row.end_date}</td>
                        <td>${row.docstatus == 1 ? "Submitted" : "Draft"}</td>
                        <td>${row.project}</td>
                        <td>${row.project_number}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;

    d.fields_dict.html_table.$wrapper.html(table_html);
    d.show();
}


frappe.ui.form.on('Stock Entry Detail', {
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