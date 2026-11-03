import json
import copy
import traceback
from io import BytesIO

import frappe
from frappe import _
from frappe.desk.query_report import get_column_as_dict, run
from frappe.utils import cint, cstr, flt, get_datetime, strip_html
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter

DATE_FIELDTYPES = {"Date"}
DATETIME_FIELDTYPES = {"Datetime"}


class _ReportFilters(frappe._dict):
    """frappe._dict that is always truthy, even when empty."""

    def __bool__(self):
        return True


def _to_report_filters(value):
    if isinstance(value, dict):
        return _ReportFilters({k: _to_report_filters(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return [_to_report_filters(v) for v in value]
    return value


def normalize_report_filters(raw):
    if raw is None or raw == "":
        return _ReportFilters()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as e:
            frappe.throw(_("Report filters are not valid JSON: {0}").format(e))
        if raw is None:
            return _ReportFilters()
    if not isinstance(raw, dict):
        frappe.throw(_("Report filters must be an object, got {0}.").format(type(raw).__name__))
    return _to_report_filters(copy.deepcopy(dict(raw)))


# ---------------------------------------------------------------------------
# Shared workbook builder + download response
# ---------------------------------------------------------------------------
def _build_and_send(title, labels, fieldnames, fieldtypes, rows, filename):
    wb = Workbook(write_only=True)
    ws = wb.create_sheet((title or "Sheet1")[:31])

    header_font = Font(bold=True, size=10)
    thin = Side(style="thin", color="D3D3D3")
    header_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    right_align = Alignment(horizontal="right", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    header_cells = []
    for label in labels:
        cell = WriteOnlyCell(ws, value=label)
        cell.font = header_font
        cell.alignment = center
        cell.border = header_border
        header_cells.append(cell)
    ws.append(header_cells)

    max_width = [min(max(len(str(lbl or "")) + 4, 12), 45) for lbl in labels]
    sample_rows = rows[:min(len(rows), 100)] if rows else []
    for row in sample_rows:
        if isinstance(row, dict):
            vals = [row.get(fn, "") for fn in fieldnames]
        elif isinstance(row, (list, tuple)):
            vals = [row[i] if i < len(row) else "" for i in range(len(fieldnames))]
        else:
            continue
        for idx, val in enumerate(vals):
            if val is not None and val != "":
                w = len(cstr(val)) + 3
                if w > max_width[idx]:
                    max_width[idx] = min(w, 45)

    for idx, width in enumerate(max_width, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    ws.freeze_panes = "A2"

    for row in rows:
        if isinstance(row, dict):
            values = [row.get(fn, "") for fn in fieldnames]
        elif isinstance(row, (list, tuple)):
            values = [row[i] if i < len(row) else "" for i in range(len(fieldnames))]
        else:
            continue

        clean_row = []
        for val, ftype in zip(values, fieldtypes):
            if isinstance(val, bool):
                val = "Yes" if val else "No"
            elif val is None:
                val = ""

            if ftype in ("Currency", "Float") and val != "":
                try:
                    num_val = flt(val, 2)
                    c = WriteOnlyCell(ws, value=num_val)
                    c.number_format = "#,##0.00"
                    c.alignment = right_align
                    clean_row.append(c)
                except (ValueError, TypeError):
                    clean_row.append(cstr(val))
            elif ftype == "Percent" and val != "":
                try:
                    pct_val = flt(val, 2) / 100.0
                    c = WriteOnlyCell(ws, value=pct_val)
                    c.number_format = "0.00%"
                    c.alignment = right_align
                    clean_row.append(c)
                except (ValueError, TypeError):
                    clean_row.append(cstr(val))
            elif ftype == "Int" and val != "":
                try:
                    int_val = cint(val)
                    c = WriteOnlyCell(ws, value=int_val)
                    c.number_format = "#,##0"
                    c.alignment = right_align
                    clean_row.append(c)
                except (ValueError, TypeError):
                    clean_row.append(cstr(val))
            elif ftype in DATE_FIELDTYPES and val:
                try:
                    d_val = get_datetime(val).date()
                    c = WriteOnlyCell(ws, value=d_val)
                    c.number_format = "yyyy-mm-dd"
                    c.alignment = center
                    clean_row.append(c)
                except Exception:
                    clean_row.append(cstr(val))
            elif ftype in DATETIME_FIELDTYPES and val:
                try:
                    dt_val = get_datetime(val)
                    c = WriteOnlyCell(ws, value=dt_val)
                    c.number_format = "yyyy-mm-dd hh:mm"
                    c.alignment = center
                    clean_row.append(c)
                except Exception:
                    clean_row.append(cstr(val))
            else:
                if isinstance(val, str):
                    if "<" in val and ">" in val:
                        val = strip_html(val)
                    if val.startswith("="):
                        val = f"'{val}"
                clean_row.append(val)

        ws.append(clean_row)

    buffer = BytesIO()
    wb.save(buffer)

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = buffer.getvalue()
    frappe.local.response.type = "download"
    frappe.local.response.content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------------------------------------------------------------------------
# 1. Query / Script Report export
# ---------------------------------------------------------------------------
@frappe.whitelist()
def export_query_report(form_params):
    if isinstance(form_params, str):
        form_params = json.loads(form_params)
    if not isinstance(form_params, dict):
        frappe.throw(_("Invalid parameters."))

    form_params = frappe._dict(form_params)
    report_name = form_params.get("report_name")
    if not report_name:
        frappe.throw(_("report_name is required."))

    report_doc = frappe.get_doc("Report", report_name)
    if not report_doc.is_permitted():
        frappe.throw(_("You don't have access to Report: {0}").format(_(report_name)), frappe.PermissionError)
    if not frappe.has_permission(report_doc.ref_doctype, "report"):
        frappe.throw(_("You don't have permission to get a report on: {0}").format(_(report_doc.ref_doctype)), frappe.PermissionError)
    if report_doc.disabled:
        frappe.throw(_("Report {0} is disabled").format(_(report_name)))

    filters = normalize_report_filters(form_params.get("filters"))

    # Normalize date_range <-> from_date / to_date
    if "date_range" in filters and isinstance(filters["date_range"], str):
        try:
            filters["date_range"] = json.loads(filters["date_range"])
        except ValueError:
            if "," in filters["date_range"]:
                filters["date_range"] = [d.strip() for d in filters["date_range"].split(",")]
            elif " to " in filters["date_range"]:
                filters["date_range"] = [d.strip() for d in filters["date_range"].split(" to ")]

    if not filters.get("date_range") and filters.get("from_date") and filters.get("to_date"):
        filters["date_range"] = [filters.get("from_date"), filters.get("to_date")]
    elif filters.get("date_range") and isinstance(filters["date_range"], (list, tuple)) and len(filters["date_range"]) == 2:
        if not filters.get("from_date"):
            filters["from_date"] = filters["date_range"][0]
        if not filters.get("to_date"):
            filters["to_date"] = filters["date_range"][1]

    data = None
    prepared_report_name = form_params.get("prepared_report_name") or filters.get("prepared_report_name")

    # 1. If explicit prepared report provided, load completed data directly
    if prepared_report_name and frappe.db.exists("Prepared Report", prepared_report_name):
        prep_doc = frappe.get_doc("Prepared Report", prepared_report_name)
        if prep_doc.status == "Completed":
            raw_data = prep_doc.get_prepared_data()
            if raw_data:
                parsed = json.loads(raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data)
                if isinstance(parsed, dict) and "columns" in parsed:
                    data = parsed
                elif isinstance(parsed, list):
                    columns = (prep_doc.columns and json.loads(prep_doc.columns)) or (parsed[0] if parsed else [])
                    data = {"columns": columns, "result": parsed}
        elif prep_doc.status in ("Queued", "Started"):
            frappe.throw(
                _("The report is still being generated in the background. Please try again once complete."),
                title=_("Report In Progress"),
            )

    # 2. Check for completed background report matching filters if prepared_report is enabled
    if not data and getattr(report_doc, "prepared_report", False):
        from frappe.core.doctype.prepared_report.prepared_report import get_completed_prepared_report
        comp_dn = get_completed_prepared_report(filters, frappe.session.user, report_doc.report_name)
        if comp_dn:
            prep_doc = frappe.get_doc("Prepared Report", comp_dn)
            raw_data = prep_doc.get_prepared_data()
            if raw_data:
                parsed = json.loads(raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data)
                if isinstance(parsed, dict) and "columns" in parsed:
                    data = parsed
                elif isinstance(parsed, list):
                    columns = (prep_doc.columns and json.loads(prep_doc.columns)) or (parsed[0] if parsed else [])
                    data = {"columns": columns, "result": parsed}

    # 3. If still no data, run query report (respecting prepared report flow if applicable)
    if not data:
        try:
            res = run(report_name, filters, are_default_filters=False)
            if res.get("prepared_report") and res.get("doc"):
                prep_doc = res["doc"]
                raw_data = prep_doc.get_prepared_data()
                if raw_data:
                    parsed = json.loads(raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data)
                    if isinstance(parsed, dict) and "columns" in parsed:
                        data = parsed
                    elif isinstance(parsed, list):
                        columns = (prep_doc.columns and json.loads(prep_doc.columns)) or (parsed[0] if parsed else [])
                        data = {"columns": columns, "result": parsed}
            elif res.get("columns"):
                data = res
            elif res.get("prepared_report") and not res.get("doc"):
                # Report is configured as prepared report but not yet generated in background.
                # Run with ignore_prepared_report=True to produce synchronous export.
                data = run(report_name, filters, ignore_prepared_report=True, are_default_filters=False)
        except (frappe.PermissionError, frappe.ValidationError):
            raise
        except Exception as e:
            frappe.log_error(message=traceback.format_exc(), title=f"Excel export failed: {report_name}")
            frappe.throw(
                _("Could not export report {0}: {1}: {2}").format(report_name, type(e).__name__, e),
                title=_("Excel export failed"),
            )

    data = frappe._dict(data or {})

    if not data.get("columns"):
        frappe.throw(
            _("Report {0} returned no data to export.").format(report_name),
            title=_("Excel export failed"),
        )

    col_dicts = [get_column_as_dict(col) for col in (data.get("columns") or [])]
    fieldnames = [c.get("fieldname") for c in col_dicts]
    labels = [c.get("label") or c.get("fieldname") for c in col_dicts]
    fieldtypes = [c.get("fieldtype") or "Data" for c in col_dicts]

    _build_and_send(
        report_name,
        labels,
        fieldnames,
        fieldtypes,
        data.get("result") or [],
        frappe.scrub(report_name) + ".xlsx",
    )


# ---------------------------------------------------------------------------
# 2. Report View export (current filters, sort, visible columns)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def export_list_view(form_params):
    if isinstance(form_params, str):
        form_params = json.loads(form_params)
    form_params = frappe._dict(form_params or {})

    doctype = form_params.get("doctype")
    if not doctype:
        frappe.throw(_("doctype is required."))

    frappe.has_permission(doctype, "export", throw=True)

    meta = frappe.get_meta(doctype)
    filters = form_params.get("filters") or []
    or_filters = form_params.get("or_filters") or []

    requested = form_params.get("columns") or []
    valid_standard = {"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"}
    columns = []
    for c in requested:
        fn = c.get("fieldname")
        if not fn or any(x["fieldname"] == fn for x in columns):
            continue
        df = meta.get_field(fn)
        if df:
            if df.fieldtype in frappe.model.no_value_fields:
                continue
            columns.append({"fieldname": fn, "label": df.label or fn, "fieldtype": df.fieldtype})
        elif fn in valid_standard:
            ftype = {
                "creation": "Datetime",
                "modified": "Datetime",
                "docstatus": "Int",
                "idx": "Int",
            }.get(fn, "Data")
            columns.append(
                {
                    "fieldname": fn,
                    "label": c.get("label") or fn.replace("_", " ").title(),
                    "fieldtype": ftype,
                }
            )

    if not columns:
        columns = [{"fieldname": "name", "label": _("ID"), "fieldtype": "Data"}]

    sort_by = form_params.get("sort_by") or "modified"
    sort_order = (form_params.get("sort_order") or "desc").lower()
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"
    if sort_by not in valid_standard and not meta.get_field(sort_by):
        sort_by = "modified"
    order_by = f"`tab{doctype}`.`{sort_by}` {sort_order}"

    rows = frappe.get_list(
        doctype,
        fields=[c["fieldname"] for c in columns],
        filters=filters,
        or_filters=or_filters,
        order_by=order_by,
        limit_page_length=0,
    )

    _build_and_send(
        doctype,
        [c["label"] for c in columns],
        [c["fieldname"] for c in columns],
        [c["fieldtype"] for c in columns],
        rows,
        frappe.scrub(doctype) + ".xlsx",
    )