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
			if (!cost_center){
                this.set_default_account("cost_center", "cost_center");
            }
			

			this.frm.refresh_fields("items");
		}
	}
}

extend_cscript(cur_frm.cscript, new erpnext.stock.StockEntry({ frm: cur_frm }));
