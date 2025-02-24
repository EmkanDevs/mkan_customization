frappe.ui.form.on("Purchase Order", {
    refresh: function (frm) {
        if (frm.doc.custom_bid_tabulation_check == 0) {
            console.log("hello")
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
    }
});
