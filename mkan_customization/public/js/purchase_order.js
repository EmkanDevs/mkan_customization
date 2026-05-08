frappe.ui.form.on("Purchase Order", {
    refresh: function (frm) {
        render_rate_mismatch_warning(frm);
        frm.add_custom_button(
            __("Service Status"),
            () => {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doc_events.purchase_order.service_status_map",
                    args: {
                        source_name: frm.doc.name
                    },
                    callback: function (response) {
                        if (response.message) {
                            frappe.model.sync(response.message);
                            frappe.set_route("Form", response.message.doctype, response.message.name);
                        }
                    }
                });
            },
            __("Create")
        );
        if (frm.doc.custom_bid_tabulation_check == 0) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Purchase Order",
                    filters: {
                        docstatus: ["<", 2],
                        bid_tabulation: frm.doc.bid_tabulation
                    },
                    fields: ["name"]
                },
                callback: function (response) {
                    let existing_docs = response.message;
                    if (existing_docs.length > 0) {
                        let po_links = existing_docs
                            .map(row => `<a href="/app/purchase-order/${row.name}" style="color:blue;">${row.name}</a>`)
                            .join("<br>");

                        frappe.confirm(
                            `The following Purchase Orders already exist for this Bid Tabulation:<br><br>${po_links}<br><br>Do you want to proceed?`,
                            () => {
                                frappe.validated = true;
                                frm.save();
                            },
                            () => {
                                frappe.validated = false;
                                if (frm.doc.bid_tabulation) {
                                    frappe.set_route("Form", "Bid Tabulation Discussion", frm.doc.bid_tabulation);
                                }
                            }
                        );

                    }
                }
            });
        }
    },

    validate(frm) {
        render_rate_mismatch_warning(frm);
    },

    items_on_form_rendered(frm) {
        render_rate_mismatch_warning(frm);
    }

});

async function render_rate_mismatch_warning(frm) {

    // HTML field must exist
    if (!frm.fields_dict.rate_mismatch_html) {
        return;
    }

    // No Bid Tabulation
    if (!frm.doc.bid_tabulation) {

        frm.fields_dict.rate_mismatch_html.$wrapper.html("");

        return;
    }

    // Fetch mismatches
    let r = await frappe.call({
        method: "mkan_customization.mkan_customization.doc_events.purchase_order.check_rate_mismatch",
        args: {
            doc: frm.doc
        }
    });

    const mismatches = r.message || [];

    // No mismatches
    if (!mismatches.length) {

        frm.fields_dict.rate_mismatch_html.$wrapper.html("");

        return;
    }

    // Build rows
    let rows = "";

    mismatches.forEach((m, idx) => {

        rows += `
            <tr>
                <td style="padding:10px;">
                    ${idx + 1}
                </td>

                <td style="padding:10px;">
                    <b>${m.item_code || ""}</b>
                </td>

                <td style="padding:10px;">
                    ${m.item_name || ""}
                </td>

                <td style="
                    padding:10px;
                    text-align:right;
                    color:#c0392b;
                    font-weight:600;
                ">
                    ${format_currency(m.sq_rate, frm.doc.currency)}
                </td>

                <td style="
                    padding:10px;
                    text-align:right;
                    color:#2471a3;
                    font-weight:600;
                ">
                    ${format_currency(m.po_rate, frm.doc.currency)}
                </td>
            </tr>
        `;
    });

    // Render HTML
    frm.fields_dict.rate_mismatch_html.$wrapper.html(`

        <div style="
            border:1px solid #f1c40f;
            border-radius:10px;
            background:#fffdf5;
            padding:16px;
            margin-top:10px;
            margin-bottom:15px;
        ">

            <div style="
                display:flex;
                align-items:center;
                gap:10px;
                margin-bottom:12px;
            ">

                <span style="
                    font-size:18px;
                ">
                    ⚠️
                </span>

                <div>

                    <div style="
                        font-size:15px;
                        font-weight:700;
                        color:#8a6d3b;
                    ">
                        Supplier Quotation Rate Mismatch
                    </div>

                    <div style="
                        font-size:13px;
                        color:#666;
                        margin-top:2px;
                    ">
                        Some Purchase Order item rates differ from the
                        linked Supplier Quotation rates.
                    </div>

                </div>

            </div>

            <div style="
                max-height:350px;
                overflow:auto;
                border:1px solid #eee;
                border-radius:6px;
            ">

                <table class="table table-bordered"
                    style="
                        margin:0;
                        width:100%;
                        font-size:13px;
                    ">

                    <thead>

                        <tr style="
                            background:#f8f9fa;
                        ">

                            <th style="padding:10px;">#</th>

                            <th style="padding:10px;">
                                Item Code
                            </th>

                            <th style="padding:10px;">
                                Item Name
                            </th>

                            <th style="
                                padding:10px;
                                text-align:right;
                            ">
                                SQ Rate
                            </th>

                            <th style="
                                padding:10px;
                                text-align:right;
                            ">
                                PO Rate
                            </th>

                        </tr>

                    </thead>

                    <tbody>
                        ${rows}
                    </tbody>

                </table>

            </div>

        </div>
    `);
}
