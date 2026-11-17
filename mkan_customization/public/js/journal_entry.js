// Party-required accounts come from the Account master (checkbox "Require Party in
// Journal Entry" + "Required Party Type"), never from hard-coded lists. The map is
// re-fetched on every form refresh, so Account changes are picked up automatically.
const PARTY_REQUIRED_METHOD =
    "mkan_customization.mkan_customization.override.journal_entry.get_party_required_accounts";
let party_required_accounts = {}; // { account: required party type }

function load_party_required_accounts(frm) {
    return frappe
        .xcall(PARTY_REQUIRED_METHOD)
        .then(map => {
            party_required_accounts = map || {};
            reset_party_grid_header(frm);
        })
        .catch(() => {
            /* keep previous map; the server re-validates on save anyway */
        });
}

function get_required_party_type(account) {
    return (account && party_required_accounts[String(account).trim()]) || null;
}

function is_employee_target_account(account) {
    return !!get_required_party_type(account);
}

frappe.ui.form.on("Journal Entry", {
    onload(frm) {
        load_party_required_accounts(frm);
    },

    refresh(frm) {
        load_party_required_accounts(frm);
        reset_party_grid_header(frm);
    },

    custom_project(frm) {
        update_project_cost_center(frm);
    },

    custom_cost_center(frm) {
        update_project_cost_center(frm);
    },

    validate(frm) {
        for (let row of (frm.doc.accounts || [])) {
            const required_type = get_required_party_type(row.account);
            if (required_type) {
                if (!row.party_type) {
                    frappe.model.set_value(row.doctype, row.name, "party_type", required_type);
                } else if (row.party_type !== required_type) {
                    frappe.msgprint({
                        title: __("Validation Error"),
                        message: __("Row {0}: Party Type must be '{1}' for account {2}", [row.idx, required_type, row.account]),
                        indicator: "red"
                    });
                    frappe.validated = false;
                    return false;
                }

                if (!row.party) {
                    frappe.msgprint({
                        title: __("Mandatory Field"),
                        message: __("Row {0}: Party Type and Party are mandatory for account {1}", [row.idx, row.account]),
                        indicator: "red"
                    });
                    frappe.validated = false;
                    return false;
                }
            }
        }
    }
});

frappe.ui.form.on("Journal Entry Account", {
    account(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        const required_type = get_required_party_type(row.account);
        if (required_type && row.party_type !== required_type) {
            frappe.model.set_value(cdt, cdn, "party_type", required_type);
        }
    },

    form_render(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let grid = frm.fields_dict.accounts && frm.fields_dict.accounts.grid;
        let grid_row = grid && grid.get_row(row.name);
        if (grid_row && grid_row.grid_form) {
            let is_emp = is_employee_target_account(row.account);
            let gf = grid_row.grid_form;
            if (gf.fields_dict.party_type) {
                gf.fields_dict.party_type.df.reqd = is_emp ? 1 : 0;
                gf.fields_dict.party_type.refresh();
            }
            if (gf.fields_dict.party) {
                gf.fields_dict.party.df.reqd = is_emp ? 1 : 0;
                gf.fields_dict.party.refresh();
            }
        }
    }
});

function reset_party_grid_header(frm) {
    if (!frm.fields_dict.accounts || !frm.fields_dict.accounts.grid) return;
    let grid = frm.fields_dict.accounts.grid;

    // Keep docfield reqd = 0 so table header does not show red asterisk globally
    (grid.docfields || []).forEach(df => {
        if (df.fieldname === "party_type" || df.fieldname === "party") {
            df.reqd = 0;
        }
    });

    if (grid.header_row) {
        $(grid.header_row.row).find(".static-area.reqd").each(function () {
            let fn = $(this).closest(".col").attr("data-fieldname");
            if (fn === "party_type" || fn === "party") {
                $(this).removeClass("reqd");
            }
        });
    }
}

function update_project_cost_center(frm) {
    (frm.doc.accounts || []).forEach(row => {
        if (frm.doc.custom_project) {
            row.project = frm.doc.custom_project;
        }

        if (frm.doc.custom_cost_center) {
            row.cost_center = frm.doc.custom_cost_center;
        }
    });

    frm.refresh_field("accounts");
}
