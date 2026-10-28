(() => {
    "use strict";

    const BUTTON_LABEL = __("Download Excel");
    const BUTTON_CLASS = "custom-download-excel-btn";
    const REPORT_URL = "/api/method/mkan_customization.mkan_customization.api.export_query_report";
    const LIST_URL   = "/api/method/mkan_customization.mkan_customization.api.export_list_view";

    function post_download(url, params) {
        const payload = { form_params: JSON.stringify(params) };
        if (typeof open_url_post === "function") {
            open_url_post(url, payload);
        } else if (frappe?.utils?.open_url_post) {
            frappe.utils.open_url_post(url, payload);
        } else {
            const form = document.createElement("form");
            form.method = "POST";
            form.action = url;
            form.style.display = "none";
            const input = document.createElement("input");
            input.name = "form_params";
            input.value = payload.form_params;
            form.appendChild(input);
            if (frappe.csrf_token && frappe.csrf_token !== "None") {
                const csrf = document.createElement("input");
                csrf.name = "csrf_token";
                csrf.value = frappe.csrf_token;
                form.appendChild(csrf);
            }
            document.body.appendChild(form);
            form.submit();
            form.remove();
        }
    }

    // ------------------------- Query Report -------------------------
    function download_report_excel(report) {
        report = report || frappe.query_report;
        if (!report || !report.report_name) {
            frappe.show_alert({ message: __("Could not detect the current report."), indicator: "red" });
            return;
        }

        let filters = {};
        try {
            if (typeof report.get_filter_values === "function") {
                filters = report.get_filter_values(true) || {};
            } else if (typeof report.get_values === "function") {
                filters = report.get_values() || {};
            }
        } catch (e) {
            return;
        }

        frappe.show_alert({ message: __("Preparing Excel..."), indicator: "green" });
        post_download(REPORT_URL, {
            report_name: report.report_name,
            filters: filters,
        });
    }

    function add_report_button(report) {
        report = report || frappe.query_report;
        if (!report?.page?.wrapper) return;
        if (report.page.wrapper.find("." + BUTTON_CLASS).length) return;
        const $btn = report.page.add_inner_button(BUTTON_LABEL, () => download_report_excel(report));
        if ($btn) $btn.addClass(BUTTON_CLASS);
    }

    function patch_query_report() {
        const QR = frappe.views?.QueryReport;
        if (!QR) return false;
        if (QR.prototype._custom_export_patched) return true;
        QR.prototype._custom_export_patched = true;

        ["refresh_report", "show"].forEach((fn) => {
            const original = QR.prototype[fn];
            if (!original) return;
            QR.prototype[fn] = async function (...args) {
                const result = await original.apply(this, args);
                add_report_button(this);
                return result;
            };
        });

        const original_render = QR.prototype.render;
        if (original_render) {
            QR.prototype.render = function (...args) {
                const result = original_render.apply(this, args);
                add_report_button(this);
                return result;
            };
        }
        return true;
    }

    // --------------------------- List View ---------------------------
    function download_list_excel(list_view) {
        if (!list_view?.doctype) {
            frappe.show_alert({ message: __("Could not detect the current list."), indicator: "red" });
            return;
        }

        const columns = (list_view.columns || [])
            .filter((c) => c.df && c.df.fieldname)
            .map((c) => ({ fieldname: c.df.fieldname, label: c.df.label }));

        // Make sure the ID is always included
        if (!columns.some((c) => c.fieldname === "name")) {
            columns.unshift({ fieldname: "name", label: __("ID") });
        }

        const filters = list_view.get_filters_for_args ? list_view.get_filters_for_args() : [];

        frappe.show_alert({ message: __("Preparing Excel..."), indicator: "green" });
        post_download(LIST_URL, {
            doctype: list_view.doctype,
            filters: filters,
            columns: columns,
            sort_by: list_view.sort_by,
            sort_order: list_view.sort_order,
        });
    }

    function add_list_button(list_view) {
        if (!list_view?.page?.wrapper) return;
        if (list_view.page.wrapper.find("." + BUTTON_CLASS).length) return;
        // Respect the Export permission
        if (!frappe.model.can_export(list_view.doctype)) return;

        const $btn = list_view.page.add_inner_button(BUTTON_LABEL, () => download_list_excel(list_view));
        if ($btn) $btn.addClass(BUTTON_CLASS);
    }

    function patch_list_view() {
        const LV = frappe.views?.ListView;
        if (!LV) return false;
        if (LV.prototype._custom_export_patched) return true;
        LV.prototype._custom_export_patched = true;

        const original_render = LV.prototype.render;
        if (original_render) {
            LV.prototype.render = function (...args) {
                const result = original_render.apply(this, args);
                add_list_button(this);
                return result;
            };
        }
        return true;
    }

    // ---------------------------- Bootstrap ----------------------------
    frappe.download_report_excel = download_report_excel;
    frappe.download_list_excel = download_list_excel;

    patch_query_report();
    patch_list_view();

    $(document).on("page-change", () => {
        patch_query_report();
        patch_list_view();
        const route = frappe.get_route();
        if (frappe.query_report && route?.[0] === "query-report") {
            setTimeout(() => add_report_button(frappe.query_report), 100);
        }
    });
})();