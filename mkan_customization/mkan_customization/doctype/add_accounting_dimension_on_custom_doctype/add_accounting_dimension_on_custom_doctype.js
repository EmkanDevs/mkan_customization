// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Add Accounting Dimension On Custom Doctype", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Apply Accounting Dimensions"),
				() => apply_dimensions(frm),
				__("Actions")
			);
			frm.add_custom_button(
				__("Remove Accounting Dimensions"),
				() => remove_dimensions(frm),
				__("Actions")
			);
		}
	},
});

function apply_dimensions(frm) {
	let selected_rows = frm.get_field('doctype_list').grid.get_selected_children();
	if (!selected_rows.length) {
		frappe.msgprint(__("Please select at least one doctype from the list."));
		return;
	}

	let doctypes = selected_rows.map(row => row.custom_doctype).filter(dt => !!dt);

	if (!doctypes.length) {
		frappe.msgprint(__("Selected rows do not have valid doctypes."));
		return;
	}

	frappe.call({
		method: "mkan_customization.mkan_customization.doc_events.accounting_dimensions.add_dimensions_for_custom_doctypes",
		args: {
			doctypes: doctypes
		},
		freeze: true,
		freeze_message: __("Applying accounting dimensions to selected doctypes..."),
		callback: () => {
			frappe.show_alert({
				message: __("Accounting dimensions applied to {0} doctypes.", [doctypes.length]),
				indicator: "green",
			});
		},
	});
}

function remove_dimensions(frm) {
	let selected_rows = frm.get_field('doctype_list').grid.get_selected_children();
	if (!selected_rows.length) {
		frappe.msgprint(__("Please select at least one doctype from the list."));
		return;
	}

	let doctypes = selected_rows.map(row => row.custom_doctype).filter(dt => !!dt);

	if (!doctypes.length) {
		frappe.msgprint(__("Selected rows do not have valid doctypes."));
		return;
	}

	frappe.call({
		method: "mkan_customization.mkan_customization.doc_events.accounting_dimensions.remove_dimensions_for_custom_doctypes",
		args: {
			doctypes: doctypes
		},
		freeze: true,
		freeze_message: __("Removing accounting dimensions from selected doctypes..."),
		callback: () => {
			frappe.show_alert({
				message: __("Accounting dimensions removed from {0} doctypes.", [doctypes.length]),
				indicator: "green",
			});
		},
	});
}
