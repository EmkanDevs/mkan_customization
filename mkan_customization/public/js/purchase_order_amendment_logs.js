// PO Amendment Log: related-log links on both POs, and a convenience action on a cancelled PO.
frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.docstatus === 2 && frappe.model.can_create("PO Amendment Log")) {
			frm.add_custom_button(__("PO Amendment Log"), () => {
				frappe.new_doc("PO Amendment Log", { cancelled_po_number: frm.doc.name });
			}, __("Create"));
		}
		frappe.call({
			method: "mkan_customization.mkan_customization.doctype.po_amendment_log.po_amendment_log.get_related_logs",
			args: { purchase_order: frm.doc.name },
		}).then((r) => {
			frm.dashboard.wrapper.find(".po-amd-links").closest(".form-dashboard-section").remove();
			const logs = r.message || [];
			if (!logs.length) return;
			const rows = logs.map((l) => {
				const orig = l.cancelled_po_number === frm.doc.name;
				const other = orig ? l.new_po_number : l.cancelled_po_number;
				return `<div><a href="/app/po-amendment-log/${encodeURIComponent(l.name)}">${frappe.utils.escape_html(l.name)}</a>
					<span class="text-muted"> &middot; ${orig ? __("Original PO") : __("Replacement PO")} &middot; ${__("with")} ${frappe.utils.escape_html(other || "")} &middot; ${__(l.workflow_status || "Draft")}</span></div>`;
			});
			frm.dashboard.add_section(`<div class="po-amd-links">${rows.join("")}</div>`, __("PO Amendment Logs"));
		});
	},
});
