const EMPLOYEE_TARGET_ACCOUNTS = [
    "1152001 - Employee Loans - CPC",
    "1152002 - Employees other deduction - CPC",
    "1157101 - Petty Cash (Business Advance) - CPC"
];

const EMPLOYEE_TARGET_NUMBERS = ["1152001", "1152002", "1157101"];

const EMPLOYEE_TARGET_NAMES = [
    "Employee Loans",
    "Employees other deduction",
    "Petty Cash (Business Advance)"
];

function is_employee_target_account(account) {
    if (!account) return false;
    let acc_str = String(account).trim();
    if (EMPLOYEE_TARGET_ACCOUNTS.includes(acc_str)) return true;

    let acc_num = acc_str.split(" - ")[0].trim();
    if (EMPLOYEE_TARGET_NUMBERS.includes(acc_num)) return true;

    for (let target_name of EMPLOYEE_TARGET_NAMES) {
        if (acc_str.includes(target_name)) return true;
    }
    return false;
}

frappe.ui.form.on("Journal Entry", {
    onload(frm) {
        reset_party_grid_header(frm);
    },

    refresh(frm) {
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
            if (is_employee_target_account(row.account)) {
                if (!row.party_type) {
                    frappe.model.set_value(row.doctype, row.name, "party_type", "Employee");
                } else if (row.party_type !== "Employee") {
                    frappe.msgprint({
                        title: __("Validation Error"),
                        message: __("Row {0}: Party Type must be 'Employee' for account {1}", [row.idx, row.account]),
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
        if (is_employee_target_account(row.account)) {
            frappe.model.set_value(cdt, cdn, "party_type", "Employee");
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
