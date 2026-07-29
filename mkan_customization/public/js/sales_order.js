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
    custom_boq(frm) {
        if (!frm.doc.custom_boq) return;

        frappe.call({
            method: "mkan_customization.mkan_customization.doc_events.sales_order.get_boq_item_map",
            args: {
                boq: frm.doc.custom_boq
            },
            callback: function (r) {
                if (!r.message) return;

                const boq_item_map = r.message;
                console.log(boq_item_map);
                frm.set_value("set_warehouse", boq_item_map.warehouse);

                frm.doc.items.forEach(row => {
                    if (boq_item_map.item_map[row.item_code]) {
                        row.custom_boq_id = boq_item_map.item_map[row.item_code];
                    }
                });

                frm.refresh_field("items");
            }
        });
    },
    refresh: function (frm) {
        frm.add_custom_button('Advance Payment Report', function () {
            frappe.set_route('query-report', 'Advance Payment', { "sales_order": frm.doc.name });
        }, "Report");
        frappe.db.get_list("Sales Order", {
            filters: {
                custom_stopped_sales_order_ref: frm.doc.name
            },
            fields: ["name", "customer", "transaction_date", "status"],
            order_by: "creation desc"
        }).then(stopped_sos => {

            if (stopped_sos.length === 0) return;

            frm.add_custom_button("Move to New SO", function () {

                // Create dialog
                const d = new frappe.ui.Dialog({
                    title: "Select Stopped Sales Order",
                    fields: [
                        {
                            label: "Newly Created SO",
                            fieldname: "stopped_so",
                            fieldtype: "Link",
                            options: "Sales Order",
                            reqd: 1,
                            get_query: () => {
                                return {
                                    filters: {
                                        custom_stopped_sales_order_ref: frm.doc.name
                                    }
                                };
                            }
                        }
                    ],
                    primary_action_label: "Move",
                    primary_action(values) {

                        if (!values.stopped_so) {
                            frappe.msgprint("Please select a Sales Order.");
                            return;
                        }

                        // Route to selected Stopped SO
                        frappe.set_route("Form", "Sales Order", values.stopped_so);

                        d.hide();
                    }
                });

                d.show();
            }, "Create");
        });

        // frm.add_custom_button(__('Move to New SO'), function () {
        //     const new_doc = frappe.model.copy_doc(frm.doc);
        //     new_doc.custom_stopped_sales_order_ref = frm.doc.name;
        //     new_doc.custom_stopped = 0;
        //     new_doc.custom_boq = frm.doc.custom_boq;

        //     frappe.model.sync(new_doc);
        //     frappe.set_route('Form', new_doc.doctype, new_doc.name);
        // }, __('Create'));


        const is_stopped = frm.doc.custom_stopped;

        // Stop button: only when not already stopped
        if (!is_stopped) {
            frm.add_custom_button('Stop', function () {
                frm.set_value('custom_stopped', 1);
                frm.save('Update').then(() => {
                    show_stopped_badge(frm);
                    frm.reload_doc();
                });
            }, "Status");
        }


        frm.add_custom_button('Retention Report', function () {
            frappe.set_route('query-report', 'Retention Report', { "sales_order": frm.doc.name });
        }, "Report");

        // Show/clear badge based on stopped state
        if (is_stopped) {
            show_stopped_badge(frm);
        } else {
            clear_badge(frm);
        }

        if (!frm.is_new()) {

            // Fetch HTML content (existing)
            frappe.call({
                method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.fetch_so_wpr_irm",
                args: { sales_order: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frm.fields_dict.custom_html_tab.$wrapper.html(r.message);
                    }
                }
            });

            // Fetch Project details first
            frappe.db.get_value("Project", frm.doc.project, ["custom_project_code", "project_name"]).then(res => {
                const project_data = res.message || {};

                // ----------- Work Progress Report ------------
                if (frm.doc.docstatus == 1) {
                    frm.add_custom_button(__('Work Progress Report'), async function () {
                        const latest_wpr = await frappe.db.get_list('Work Progress Report', {
                            filters: {
                                sales_order: frm.doc.name,
                                docstatus: ["!=", 2] // ✅ ignore cancelled docs
                            },
                            fields: ['name', 'version'],
                            order_by: 'creation desc',
                            limit: 1
                        });

                        let next_version = 1;
                        let details = [];

                        if (!latest_wpr.length) {
                            // First WPR → use SO items
                            next_version = 1;
                            (frm.doc.items || []).forEach(row => {
                                details.push({
                                    item: row.item_code,
                                    item_name: row.item_name,
                                    boq_details: row.custom_boq_details || '',
                                     boq_details_id: row.custom_boq_id || '',
                                    item_code: row.item_code,
                                    description: row.description,
                                    total_quantities_implemented: row.qty,
                                    version: next_version,
                                    rate: row.rate,
                                    amount: row.amount,
                                    uom: row.uom,
                                });
                            });
                        } else {
                            // Subsequent WPRs → copy from previous
                            next_version = parseInt(latest_wpr[0].version) + 1;
                            const previous_wpr = await frappe.db.get_doc('Work Progress Report', latest_wpr[0].name);

                            details = previous_wpr.work_progress_detail.map(d => ({
                                item: d.item,
                                item_name: d.item_name,
                                item_code: d.item_code,
                                description: d.description,
                                total_quantities_implemented: d.total_quantities_implemented,
                                completion_rate: d.completion_rate,
                                previous_executed_quantity: d.previous_executed_quantity,
                                current_executed_quantity: d.current_executed_quantity,
                                version: next_version,
                                rate: d.rate,
                                amount: d.amount,
                                uom: d.uom
                            }));
                        }

                        // ✅ Proper way: create and fill the doc BEFORE routing
                        frappe.model.with_doctype('Work Progress Report', function () {
                            let new_doc = frappe.model.get_new_doc('Work Progress Report');

                            Object.assign(new_doc, {
                                sales_order: frm.doc.name,
                                naming_series: "SO-",
                                project: frm.doc.project,
                                customer: frm.doc.customer,
                                start_date: frm.doc.transaction_date,
                                end_date: frm.doc.delivery_date,
                                project_code: frm.doc.custom_project_code || "",
                                project_name: frm.doc.project,
                                version: next_version
                            });

                            // Add child table rows
                            details.forEach(d => {
                                const child = frappe.model.add_child(new_doc, "Work Progress Detail", "work_progress_detail");
                                Object.assign(child, d);
                            });

                            frappe.set_route("Form", new_doc.doctype, new_doc.name);
                        });
                    }, __("Create"));
                }

                // ----------- Invoice Released Memo ------------
                if (frm.doc.docstatus == 1 && frm.doc.custom_stopped != 1) {
                    frm.add_custom_button(__('Invoice released Memo'), async function () {
                        const latest_irm = await frappe.db.get_list('Invoice released Memo', {
                            filters: {
                                sales_order: frm.doc.name,
                                docstatus: ["!=", 2]
                            },
                            fields: ['name', 'version', 'docstatus'],
                            order_by: 'creation desc',
                            limit: 1
                        });

                        console.log("IRM count:", latest_irm.length);

                        if (latest_irm.length) {
                            console.log("Docstatus:", latest_irm[0].docstatus);
                        }

                        // Block creation only if previous IRM is in draft
                        if (latest_irm.length && latest_irm[0].docstatus === 0) {
                            frappe.msgprint({
                                title: __("Not Allowed"),
                                message: __("Action not allowed as the previous Invoice released Memo is in draft mode."),
                                indicator: "red"
                            });
                            return;
                        }

                        let next_version = 1;
                        let details = [];

                        if (!latest_irm.length) {
                            // First IRM → use SO items
                            next_version = 1;
                            (frm.doc.items || []).forEach(row => {
                                details.push({
                                    item: row.item_code || '',
                                    item_name: row.item_name || '',
                                    boq_details: row.custom_boq_details || '',
                                    boq_details_id: row.custom_boq_id || '',
                                    description: row.description || '',
                                    contract__quantity: flt(row.qty),
                                    unit_rate: flt(row.rate),
                                    contract_price: flt(row.amount) || (flt(row.qty) * flt(row.rate)),
                                    accumulate_quantity: 0,
                                    uom: row.uom || row.stock_uom || '',
                                    boq_id: frm.doc.custom_boq || ''   // ✅ New: set custom_boq from SO
                                });
                            });
                        } else {
                            // Subsequent IRMs → copy from previous version
                            next_version = parseInt(latest_irm[0].version) + 1;
                            const previous_irm = await frappe.db.get_doc('Invoice released Memo', latest_irm[0].name);
                            let so_item_map = {};
                            // (frm.doc.items || []).forEach(row => {
                            //     so_item_map[row.item_code] = row.qty;
                            // });
                            details = previous_irm.invoice_released_memo_detail.map(d => ({
                                item: d.item,
                                item_name: d.item_name,
                                description: d.description,
                                contract__quantity: d.contract__quantity,
                                unit: d.unit,
                                unit_rate: d.unit_rate,
                                boq_details:d.boq_details,
                                boq_details_id:d.boq_details_id,
                                // contract_price: d.contract_price,
                                // current_quantity: d.current_quantity,
                                version: next_version,
                                accumulate_quantity: 0,
                                previous_quantity: d.accumulate_final_quantity,
                                // accumulate_final_quantity: d.accumulate_final_quantity,
                                progress_percentage: d.progress_percentage,
                                progress_completion: d.progress_completion + d.progress_percentage,
                                previous: d.accumulated + d.previous,
                                // current: d.current,
                                // accumulated: d.accumulated,
                                uom: d.uom,
                                boq_id: frm.doc.custom_boq || ''
                                   // ✅ Also set it for copied rows
                            }));
                        }

                        // ✅ Create document manually (so we can add children before routing)
                        const new_doc = frappe.model.get_new_doc("Invoice released Memo");

                        // Assign SO-related fields (these will persist after refresh)
                        Object.assign(new_doc, {
                            sales_order: frm.doc.name,
                            created_from: "Sales Order",
                            naming_series: "SO-",
                            vate_rate: frm.doc.taxes_and_charges,
                            project: frm.doc.project,
                            client: frm.doc.customer,
                            start_date: frm.doc.transaction_date,
                            end_date: frm.doc.delivery_date,
                            project_code: project_data.custom_project_code,
                            project_name: project_data.project_name,
                            retention: frm.doc.retention,
                            advanced_payment_recovery: frm.doc.advance_payment,
                            version: next_version
                        });

                        // Add child rows
                        details.forEach(d => {
                            const child = frappe.model.add_child(new_doc, "Invoice Released Memo Detail", "invoice_released_memo_detail");
                            Object.assign(child, d);
                        });

                        frappe.model.sync(new_doc);
                        frappe.set_route("Form", new_doc.doctype, new_doc.name);
                    }, __("Create"));
                }
            });
        }
    }
});

function calculate_retention(frm) {
    const total = frm.doc.total || 0;
    const retention_percent = frm.doc.retention || 0;
    const custom_retention_amount = (total * retention_percent) / 100;
    frm.set_value('custom_retention_amount', custom_retention_amount);
}

function create_badge_container(frm) {
    if (!frm.custom_badge_container) {
        frm.custom_badge_container = $('<div style="display:inline-block; margin-left: 10px;"></div>')
            .appendTo(frm.page.wrapper.find('.title-area'));
    }
}
function clear_badge(frm) {
    if (frm.custom_badge_container) {
        frm.custom_badge_container.empty();
    }
}
function show_stopped_badge(frm) {
    create_badge_container(frm);

    frm.custom_badge_container.html(`
        <span style="
            display: inline-block;
            background-color: #dc3545;
            color: white;
            padding: 3px 10px;
            font-size: 0.85rem;
            font-weight: 600;
            border-radius: 12px;
            box-shadow: 0 0 5px rgba(220, 53, 69, .5);
            white-space: nowrap;">
            Stopped
        </span>
    `);
}





frappe.ui.form.on('Sales Order Item', {
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