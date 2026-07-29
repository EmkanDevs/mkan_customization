# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class RentalEquipmentTimesheet(Document):
	pass


import frappe
import pandas as pd
import os
from frappe import _
from frappe.utils import getdate, today, flt, get_time


@frappe.whitelist()
def mass_submit_rental_equipment_timesheets(names):
    if isinstance(names, str):
        import json
        names = json.loads(names)

    count = 0
    errors = []

    for name in names:
        try:
            doc = frappe.get_doc("Rental Equipment Timesheet", name)
            if doc.docstatus == 0:  # Only submit Drafts
                doc.submit()
                count += 1
        except Exception as e:
            errors.append(f"Error submitting {name}: {str(e)}")

    if errors:
        frappe.msgprint({
            "title": _("Partial Success"),
            "indicator": "orange",
            "message": _("Submitted {0} docs. Errors encountered:<br>{1}").format(count, "<br>".join(errors))
        })

    return count


@frappe.whitelist()
def upload_rental_equipment_timesheet(file_url):
    """
    Reads an Excel file and creates Rental Equipment Timesheet documents.

    Expected Excel columns (row 1 = headers):
        Month | Project | Contract # | Category | Iqama | Plate Number |
        Name | Job | Supplier | Date | Time In | Time Out |
        Normal Hours | Over Time Hours | Remarks
    """

    # ── 1. RESOLVE FILE PATH ────────────────────────────────────────────────
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    ext = os.path.splitext(file_path)[1].lower()

    # ── 2. READ FILE ─────────────────────────────────────────────────────────
    try:
        if ext == ".csv":
            df = None
            for enc in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except (UnicodeDecodeError, TypeError):
                    continue
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path, engine="openpyxl")
        else:
            frappe.throw(_("Unsupported file type: {0}. Please upload .xlsx or .csv").format(ext))

        if df is None:
            frappe.throw(_("Could not read file. Please check the file encoding or format."))

    except Exception as e:
        frappe.throw(_("Error reading file: {0}").format(str(e)))

    # ── 3. NORMALIZE HEADERS ──────────────────────────────────────────────────
    # Strip whitespace and non-breaking spaces from column names
    df.columns = [str(c).strip().replace("\xa0", " ") for c in df.columns]

    # ── 4. VALIDATE REQUIRED COLUMNS ─────────────────────────────────────────
    required_cols = ["Name", "Date"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        frappe.throw(
            _("Missing required column(s): {0}. Found columns: {1}").format(
                ", ".join(missing), ", ".join(df.columns.tolist())
            )
        )

    # ── 5. CLEAN DATA ─────────────────────────────────────────────────────────
    df = df.applymap(lambda x: str(x).strip().replace("\xa0", " ") if pd.notna(x) else "")

    created = []
    skipped = []

    # ── 6. LOOP ROWS AND CREATE DOCS ──────────────────────────────────────────
    for i, row in df.iterrows():
        row_num = i + 2  # human-readable row number (1-indexed + header)

        # Skip completely empty rows
        equipment_name = row.get("Name", "")
        if not equipment_name or equipment_name.lower() in ["nan", ""]:
            continue

        try:
            # ── Date ────────────────────────────────────────────────────────
            raw_date = row.get("Date", "")
            if not raw_date or raw_date.lower() in ["nan", ""]:
                row_date = getdate(today())
            else:
                # Handle Excel serial date numbers (e.g., 46143)
                try:
                    row_date = getdate(raw_date)
                except Exception:
                    # Try parsing as Excel serial date
                    from datetime import datetime, timedelta
                    try:
                        serial = int(float(raw_date))
                        row_date = datetime(1899, 12, 30) + timedelta(days=serial)
                        row_date = getdate(row_date)
                    except Exception:
                        row_date = getdate(today())

            # ── Month ───────────────────────────────────────────────────────
            month = row.get("Month", "")
            if month.lower() in ["nan", ""]:
                month = None

            # ── Project ─────────────────────────────────────────────────────
            project_name = row.get("Project", "")
            if project_name.lower() in ["nan", ""]:
                project_name = None

            # ── Contract # ────────────────────────────────────────────────────
            contract_id = row.get("Contract #", "")
            if contract_id.lower() in ["nan", ""]:
                contract_id = None

            # ── Category ──────────────────────────────────────────────────────
            category = row.get("Category", "")
            if category.lower() in ["nan", ""]:
                category = None

            # ── Iqama ───────────────────────────────────────────────────────
            iqama = row.get("Iqama", "")
            if iqama.lower() in ["nan", ""]:
                iqama = None

            # ── Plate Number ──────────────────────────────────────────────────
            plate_number = row.get("Plate Number", "")
            if plate_number.lower() in ["nan", ""]:
                plate_number = None

            # ── Job ───────────────────────────────────────────────────────────
            job = row.get("Job", "")
            if job.lower() in ["nan", ""]:
                job = None

            # ── Supplier Name ───────────────────────────────────────────────
            supplier_name = row.get("Supplier", "")
            if supplier_name.lower() in ["nan", ""]:
                supplier_name = None
            # Validate supplier exists in Supplier master
            if supplier_name and not frappe.db.exists("Supplier", supplier_name):
                supplier_name = None  # Leave blank if not found

            # ── Time In ───────────────────────────────────────────────────────
            time_in = row.get("Time In", "")
            if time_in.lower() in ["nan", ""]:
                time_in = None
            else:
                try:
                    time_in = get_time(time_in)
                except Exception:
                    time_in = None

            # ── Time Out ──────────────────────────────────────────────────────
            time_out = row.get("Time Out", "")
            if time_out.lower() in ["nan", ""]:
                time_out = None
            else:
                try:
                    time_out = get_time(time_out)
                except Exception:
                    time_out = None

            # ── Normal Hours ────────────────────────────────────────────────
            raw_hours = row.get("Normal Hours", "")
            hours = flt(raw_hours) if raw_hours not in ["nan", ""] else 0.0

            # ── Over Time Hours ───────────────────────────────────────────────
            raw_ot = row.get("Over Time Hours", "")
            overtime_hours = flt(raw_ot) if raw_ot not in ["nan", ""] else 0.0

            # ── Remarks ───────────────────────────────────────────────────────
            remark = row.get("Remarks", "")
            if remark.lower() in ["nan", ""]:
                remark = None

            # ── Create Document ─────────────────────────────────────────────
            doc = frappe.new_doc("Rental Equipment Timesheet")

            # Map fields — fieldnames match what you see in the DocType Form
            doc.date              = row_date
            doc.equipment_name    = equipment_name
            doc.month             = month
            doc.hours             = hours
            doc.overtime_hours    = overtime_hours

            if project_name:
                doc.project_name  = project_name

            if contract_id:
                doc.contract_id   = contract_id

            if category:
                doc.category      = category

            if iqama:
                doc.iqama         = iqama

            if plate_number:
                doc.door_no_or_plate_no = plate_number

            if job:
                doc.job           = job

            if supplier_name:
                doc.supplier_name = supplier_name

            if time_in:
                doc.time_in       = time_in

            if time_out:
                doc.time_out      = time_out

            if remark:
                doc.remark        = remark

            doc.insert(ignore_permissions=True)
            created.append(doc.name)

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Rental Equipment Timesheet Upload Error")
            skipped.append(f"Row {row_num} ({equipment_name}): {str(e)}")

    # ── 7. COMMIT AND RETURN ──────────────────────────────────────────────────
    frappe.db.commit()

    return {"created": created, "skipped": skipped}


@frappe.whitelist()
def download_rental_equipment_timesheet_template():
    from frappe.utils.xlsxutils import make_xlsx

    columns = [
        "Month",
        "Project",
        "Contract #",
        "Category",
        "Iqama",
        "Plate Number",
        "Name",
        "Job",
        "Supplier",
        "Date",
        "Time In",
        "Time Out",
        "Normal Hours",
        "Over Time Hours",
        "Remarks",
    ]

    data = [columns]  # Header row only — user fills the rest

    xlsx_file = make_xlsx(data, "Rental Equipment Timesheet Template")

    frappe.response["filename"]    = "Rental_Equipment_Timesheet_Template.xlsx"
    frappe.response["filecontent"] = xlsx_file.getvalue()
    frappe.response["type"]        = "binary"