frappe.ui.form.on("Blanket Order", {
	refresh:function(frm){
		if (frm.doc.supplier && frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Purchase Invoice"),
				function () {
					frappe.model.open_mapped_doc({
						method: "erpnext.manufacturing.doctype.blanket_order.blanket_order.make_order",
						frm: frm,
						args: {
							doctype: "Purchase Invoice",
						},
					});
				},
				__("Create")
			);
		}
	},
});
