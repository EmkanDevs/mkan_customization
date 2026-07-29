// // Copyright (c) 2025, Finbyz and contributors
// // For license information, please see license.txt


frappe.ui.form.on('Invoice released Memo', {

    project_name: function(frm) {
        if (frm.doc.project_name) {
            update_child_projects(frm);
        }
    },

    refresh(frm) {
        calculate_total_deductions(frm);
    },

    supplied_material_total: calculate_total_deductions,
    safety: calculate_total_deductions,
    quality: calculate_total_deductions,
    other_deductions: calculate_total_deductions,
    other_warranty: calculate_total_deductions,


    
    // 2. Trigger when the Sales Order is selected (the source of the fetch)
    sales_order: function(frm) {
        // We add a slight delay to allow the 'fetch from' to finish
        setTimeout(() => {
            if (frm.doc.project_name) {
                update_child_projects(frm);
            }
        }, 500);
    },

    select_items: function (frm) {
        show_item_selector_dialog(frm);
    },
    project_sub_contracts(frm) {
        toggle_party_fields(frm);
    },

    sales_order(frm) {
        toggle_party_fields(frm);
    },
    refresh(frm) {
        toggle_party_fields(frm)
        if (frm.doc.vendor) {
            frm.add_custom_button("View Stock Entries", () => {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.get_stock_entries_irm",
                    args: {
                        project_name: frm.doc.project_name,
                        vendor: frm.doc.vendor,
                        posting_date: frm.doc.date,
                    },
                    callback(r) {
                        if (r.message && r.message.length > 0) {
                            console.log(r.message)
                            show_stock_entries_popup(r.message);

                        } else {
                            frappe.msgprint("No Stock Entries found.");
                        }
                    }
                });
            });
            frm.add_custom_button("View Stock Entry Items", () => {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.get_stock_entry_items_irm",
                    args: {
                        project_name: frm.doc.project_name,
                        vendor: frm.doc.vendor,
                        posting_date: frm.doc.date,
                    },
                    callback(r) {
                        if (r.message && r.message.length > 0) {
                            console.log(r.message)
                            show_stock_entry_items_popup(r.message);
                        } else {
                            frappe.msgprint("No Stock Entry Items found.");
                        }
                    }
                });
            });
        }
        if (frm.doc.sales_order) {
            frm.add_custom_button("Sales Order", () => {

                if (!frm.doc.sales_order) {
                    frappe.msgprint("Please select a Sales Order first.");
                    return;
                }

                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.invoice_released_memo.invoice_released_memo.get_items_from_sales_order",
                    args: { sales_order: frm.doc.sales_order },
                    callback: function (r) {

                        if (!r.message || !r.message.length) {
                            frappe.msgprint("No items found in this Sales Order.");
                            return;
                        }

                        let so_items = r.message;

                        // existing item values from child table
                        let existing_items = (frm.doc.invoice_released_memo_detail || [])
                            .map(d => d.item);

                        so_items.forEach(item => {
                            if (!existing_items.includes(item.item)) {

                                let child = frm.add_child("invoice_released_memo_detail");
                                child.boq_id = item.boq_id;
                                child.item = item.item;
                                child.description = item.description;
                                child.unit = item.unit;
                                child.contract__quantity = item.contract__quantity;
                                child.unit_rate = item.unit_rate;
                                child.contract_price = item.contract_price;
                            }
                        });

                        frm.refresh_field("invoice_released_memo_detail");
                        frappe.msgprint("Items added successfully.");
                    }
                });

            }, __("Get Items From"));
        }

        if (frm.doc.project_sub_contracts) {
            frm.add_custom_button("Project Sub-Contract", () => {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.invoice_released_memo.invoice_released_memo.get_items_from_sub_contract",
                    args: { project_sub_contracts: frm.doc.project_sub_contracts },
                    callback: function (r) {

                        if (!r.message || !r.message.length) {
                            frappe.msgprint("No items found in this Sales Order.");
                            return;
                        }

                        let so_items = r.message;

                        // existing item values from child table
                        let existing_items = (frm.doc.invoice_released_memo_detail || [])
                            .map(d => d.item);

                        so_items.forEach(item => {
                            if (!existing_items.includes(item.item)) {

                                let child = frm.add_child("invoice_released_memo_detail");
                                child.item = item.item;
                                child.unit = item.unit;
                                child.contract__quantity = item.contract__quantity;
                                child.contract_price = item.contract_price;
                            }
                        });

                        frm.refresh_field("invoice_released_memo_detail");
                        frappe.msgprint("Items added successfully.");
                    }
                });

            }, __("Get Items From"));
        }

        if (frm.doc.sales_order) {
            frm.set_df_property("supplier_materials", "hidden", 1);
            frm.set_df_property("discpline", "hidden", 1);
        } else {
            frm.set_df_property("supplier_materials", "hidden", 0);
            frm.set_df_property("discpline", "hidden", 0);
        }
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Payment Request'), function () {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.invoice_released_memo.invoice_released_memo.make_irm_payment_request",
                    args: {
                        docname: frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.model.sync(r.message);
                            frappe.show_alert({
                                message: __("Payment Request {0} created as Draft", [r.message.name]),
                                indicator: "green"
                            });
                            frappe.set_route("Form", "Payment Requester", r.message.name);
                        }
                    }
                });
            }, __("Create"));
            frm.add_custom_button(__('Create Sales Invoice'), function () {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.invoice_released_memo.invoice_released_memo.create_sales_invoice_draft",
                    args: {
                        source_name: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __("Creating Sales Invoice Draft..."),
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint({
                                title: __("Success"),
                                message: __("Sales Invoice Draft Created: ") + r.message,
                                indicator: "green"
                            });
                            frappe.set_route("Form", "Sales Invoice", r.message);
                        }
                    }
                });
            }, __("Create"));

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
                            callback: function (r) {
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

function toggle_party_fields(frm) {
    // Hide client if project_sub_contracts is populated
    if (frm.doc.project_sub_contracts) {
        frm.set_df_property('client', 'hidden', 1);
    } else {
        frm.set_df_property('client', 'hidden', 0);
    }

    // Hide vendor if sales_order is populated
    if (frm.doc.sales_order) {
        frm.set_df_property('vendor', 'hidden', 1);
    } else {
        frm.set_df_property('vendor', 'hidden', 0);
    }
}

frappe.ui.form.on('Invoice Released Memo Detail', {

    invoice_released_memo_detail_add: function(frm, cdt, cdn) {
        if (frm.doc.project_name) {
            frappe.model.set_value(cdt, cdn, 'project', frm.doc.project_name);
        }
    },

    contract__quantity: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_values(row);
        frm.refresh_field('invoice_released_memo_detail');
    },
    progress_percentage(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.progress_percentage > 100) {
            frappe.msgprint(__('Progress Percentage cannot be more than 100'));
            frappe.model.set_value(cdt, cdn, 'progress_percentage', 100);
        }
    },
    unit_rate: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_values(row);
        frm.refresh_field('invoice_released_memo_detail');
    },
    current_quantity: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_row_values(row);
        frm.refresh_field('invoice_released_memo_detail');
    },
    previous_quantity: function (frm, cdt, cdn) {
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

function show_item_selector_dialog(frm) {
    const child_table = frm.doc.invoice_released_memo_detail || [];

    if (!child_table.length) {
        frappe.msgprint(__('No items available in the child table.'));
        return;
    }

    // Track which items are checked across filters
    const selected_rows_map = {};

    const d = new frappe.ui.Dialog({
        title: 'Select Material Request',
        fields: [
            {
                fieldname: 'item_search',
                fieldtype: 'Data', // plain text input
                label: 'Search Item',
                description: __('Search and filter items below')
            },
            {
                fieldname: 'items_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: 'Get Items',
        primary_action() {
            const selected_rows = Object.keys(selected_rows_map)
                .map(name => child_table.find(r => r.name === name))
                .filter(Boolean);

            if (!selected_rows.length) {
                frappe.msgprint(__('Please select at least one item.'));
                return;
            }

            frm.clear_table('invoice_released_memo_detail');
            selected_rows.forEach((row, i) => {
                const new_row = frm.add_child('invoice_released_memo_detail');
                Object.keys(row).forEach(key => {
                    if (!['name', 'owner', 'creation', 'modified', 'modified_by', 'docstatus', 'parent', 'parentfield', 'parenttype', 'idx'].includes(key)) {
                        new_row[key] = row[key];
                    }
                });
                new_row.idx = i + 1; // reset serial number
            });
            frm.refresh_field('invoice_released_memo_detail');
            d.hide();
        }
    });

    // render the table
    function render_table(filtered_rows) {
        const table_html = `
            <div style="border: 1px solid var(--muted-foreground); border-radius:6px; padding:8px;">
                <table class="table table-bordered" style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background: transparent;">
                            <th style="width: 36px; text-align:center;"><input type="checkbox" id="dialog-select-all"></th>
                            <th style="width:220px;">Item</th>
                            <th style="width:300px;">Description</th>
                            <th style="width:80px; text-align:right;">Qty</th>
                            <th style="width:120px; text-align:right;">Amount</th>
                        </tr>
                    </thead>
                </table>
                <div id="dialog-table-body" style="max-height:360px; overflow:auto; margin-top:6px;">
                    <table class="table table-bordered" style="width:100%; border-collapse:collapse;">
                        <tbody>
                            ${filtered_rows.map(row => `
                                <tr data-name="${row.name}">
                                    <td style="width:36px; text-align:center;">
                                        <input type="checkbox" class="row-checkbox" ${selected_rows_map[row.name] ? 'checked' : ''}>
                                    </td>
                                    <td style="width:220px; padding:8px;">${frappe.utils.escape_html(row.item || '')}</td>
                                    <td style="width:300px; padding:8px;">${frappe.utils.escape_html(row.description || row.item_name || '')}</td>
                                    <td style="width:80px; text-align:right; padding:8px;">${row.contract__quantity || 0}</td>
                                    <td style="width:120px; text-align:right; padding:8px;">${row.contract_price || 0}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        const $html = d.fields_dict.items_html.$wrapper;
        $html.empty().append(table_html);

        // ✅ Select-all logic
        $html.find('#dialog-select-all').on('change', function () {
            const checked = $(this).is(':checked');
            $html.find('.row-checkbox').prop('checked', checked);
            filtered_rows.forEach(r => {
                if (checked) selected_rows_map[r.name] = true;
                else delete selected_rows_map[r.name];
            });
        });

        // ✅ Row click toggling
        $html.find('tr[data-name]').on('click', function (e) {
            if ($(e.target).is('input')) return;
            const $cb = $(this).find('.row-checkbox');
            const checked = !$cb.prop('checked');
            $cb.prop('checked', checked);
            const rowname = $(this).data('name');
            if (checked) selected_rows_map[rowname] = true;
            else delete selected_rows_map[rowname];
        });

        // ✅ Direct checkbox clicks
        $html.find('.row-checkbox').on('change', function () {
            const rowname = $(this).closest('tr').data('name');
            if ($(this).is(':checked')) selected_rows_map[rowname] = true;
            else delete selected_rows_map[rowname];
        });
    }

    // Initial render
    render_table(child_table);

    // Filter when user selects/inputs in search
    d.fields_dict.item_search.$input.on('input change', function () {
        const val = d.get_value('item_search') || '';
        const lower = val.toString().toLowerCase();

        const filtered = child_table.filter(r => {
            if (!val) return true;
            return (
                (r.item && r.item.toLowerCase().includes(lower)) ||
                (r.item_name && r.item_name.toLowerCase().includes(lower)) ||
                (r.description && r.description.toLowerCase().includes(lower))
            );
        });

        render_table(filtered);
    });

    d.show();
}

function show_stock_entries_popup(data) {
    let d = new frappe.ui.Dialog({
        title: "Stock Entries (Send to Subcontractor)",
        size: "extra-large",
        fields: [
            { fieldname: "html_table", fieldtype: "HTML" }
        ]
    });

    let table_html = `
        <table class="table table-bordered table-hover">
            <thead>
                <tr>
                    <th>Stock Entry</th>
                    <th>Supplier</th>
                    <th>Posting Date</th>
                    <th>From Warehouse</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(row => `
                    <tr>
                        <td><a href="/app/stock-entry/${row.name}" target="_blank">${row.name}</a></td>
                        <td>${row.custom_supplier_code || ''}</td>
                        <td>${row.posting_date || ''}</td>
                        <td>${row.from_warehouse || ''}</td>
                        <td>${row.docstatus == 1 ? "Submitted" : "Draft"}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;

    d.fields_dict.html_table.$wrapper.html(table_html);
    d.show();
}

function show_stock_entry_items_popup(data) {
    let d = new frappe.ui.Dialog({
        title: "Stock Entry Items (Send to Subcontractor)",
        size: "extra-large",
        fields: [
            { fieldname: "html_table", fieldtype: "HTML" }
        ]
    });

    let table_html = `
        <table class="table table-bordered table-hover">
            <thead>
                <tr>
                    <th>Parent</th>
                    <th>Item Code</th>
                    <th>Item Name</th>
                    <th>Quantity</th>
                    <th>UOM</th>
                    <th>Basic Rate</th>
                    <th>Source Warehouse</th>
                    <th>Target Warehouse</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(row => `
                    <tr>
                        <td><a href="/app/stock-entry/${row.parent}" target="_blank">${row.parent}</a></td>
                        <td>${row.item_code || ''}</td>
                        <td>${row.item_name || ''}</td>
                        <td>${row.qty || 0}</td>
                        <td>${row.uom || ''}</td>
                        <td>${row.basic_rate || 0}</td>
                        <td>${row.s_warehouse || ''}</td>
                        <td>${row.t_warehouse || ''}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;

    d.fields_dict.html_table.$wrapper.html(table_html);
    d.show();
}

function calculate_total_deductions(frm) {
    let total =
        (frm.doc.supplied_material_total || 0) +
        (frm.doc.safety || 0) +
        (frm.doc.quality || 0) +
        (frm.doc.other_deductions || 0) +
        (frm.doc.other_warranty || 0);

    frm.set_value('total_deductions', total);
}

var update_child_projects = function(frm) {
    frm.doc.invoice_released_memo_detail.forEach(row => {
        frappe.model.set_value(row.doctype, row.name, 'project', frm.doc.project_name);
    });
    frm.refresh_field('invoice_released_memo_detail');
};