// your_app/public/js/purchase_invoice.js
frappe.ui.form.on("Purchase Invoice", {
    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            // remove ERPNext's default entries so we don't get duplicates
            frm.page.remove_inner_button(__("Purchase Order"), __("Get Items From"));
            frm.page.remove_inner_button(__("Purchase Receipt"), __("Get Items From"));

            frm.add_custom_button(__("Purchase Order"), () => {
                open_get_items_dialog(frm, "Purchase Order", "mkan_customization.mkan_customization.doc_events.query.po_query_with_totals",
                    "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice");
            }, __("Get Items From"));

            frm.add_custom_button(__("Purchase Receipt"), () => {
                open_get_items_dialog(frm, "Purchase Receipt", "mkan_customization.mkan_customization.doc_events.query.pr_query_with_totals",
                    "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice");
            }, __("Get Items From"));
        }
    }
});

function open_get_items_dialog(frm, source_doctype, query_method, mapper_method) {
    const date_field = source_doctype === "Purchase Receipt" ? "posting_date" : "transaction_date";

    new frappe.ui.form.MultiSelectDialog({
        doctype: source_doctype,
        target: frm,
        setters: { supplier: frm.doc.supplier || null },
        add_filters_group: 1,                     // restores "+ Add a Filter" / "Clear Filters"
        date_field: date_field,
        allow_child_item_selection: 1,             // restores "Select Purchase Order Item" checkbox
        child_fieldname: "items",
        child_columns: ["item_code", "item_name", "qty", "rate", "amount"],
        columns: ["name", date_field, "supplier", "total", "grand_total", "status"],
        get_query() {
            return {
                query: query_method,
                filters: { supplier: frm.doc.supplier || undefined }
            };
        },
        action(selections, args) {
            if (!selections.length) return;

            let mapper_args = {};
            if (args && args.filtered_children && args.filtered_children.length) {
                mapper_args = {
                    filtered_children: args.filtered_children,
                    child_docname: "items"
                };
            }

            frappe.call({
                method: "frappe.model.mapper.map_docs",
                args: {
                    method: mapper_method,
                    source_names: selections,
                    target_doc: frm.doc,
                    args: mapper_args
                },
                callback: (r) => {
                    frappe.model.sync(r.message);
                    frm.dirty();
                    frm.refresh();
                }
            });
        }
    });
}