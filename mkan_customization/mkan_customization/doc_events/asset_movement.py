import json

import frappe
from mkan_customization.mkan_customization.override.asset import get_asset_project, get_asset_department
from frappe.utils import cstr, getdate, today

def _get_latest_movement(asset):
    """Latest submitted Asset Movement for this asset, from any reference."""
    result = frappe.db.sql(
        """
        SELECT am.name, am.transaction_date
        FROM `tabAsset Movement` am
        INNER JOIN `tabAsset Movement Item` ami ON ami.parent = am.name
        WHERE am.docstatus = 1 AND ami.asset = %s
        ORDER BY am.transaction_date DESC, am.creation DESC
        LIMIT 1
        """,
        asset,
        as_dict=True,
    )
    return result[0] if result else None

def _rows_needing_movement(doc):
    """Assignment rows that are new (or edited, with no live movement) and have a
    project or location."""
    previous_doc = doc.get_doc_before_save()
    previous_rows = {
        r.name: r
        for r in (previous_doc.get("custom_asset_assignment") if previous_doc else None) or []
    }

    rows = []
    for row in doc.get("custom_asset_assignment") or []:
        if not (row.get("project") or row.get("location")):
            continue
        if _movement_is_active(row.get("custom_asset_movement")):
            continue

        old = previous_rows.get(row.name)
        if old and all(
            cstr(old.get(f)) == cstr(row.get(f)) for f in ("project", "location", "from_date")
        ):
            continue

        rows.append(row)
    return rows

def validate_single_new_assignment_row(doc, method=None):
    """IT Asset Management validate: one new assignment row per save, and its
    from_date cannot be earlier than the asset's last movement."""
    previous_doc = doc.get_doc_before_save()
    old_names = {
        r.name
        for r in (previous_doc.get("custom_asset_assignment") if previous_doc else None) or []
    }

    new_rows = [
        r for r in doc.get("custom_asset_assignment") or []
        if r.name not in old_names
    ]

    if len(new_rows) > 1:
        frappe.throw(
            "Please add only one Asset Assignment row at a time. "
            f"You added {len(new_rows)} rows (#{', #'.join(str(r.idx) for r in new_rows)}). "
            "Save after each row."
        )

    if not new_rows or not doc.asset:
        return

    row = new_rows[0]
    if not row.get("from_date"):
        return

    last = _get_latest_movement(doc.asset)
    if last and getdate(row.from_date) < getdate(last.transaction_date):
        frappe.throw(
            f"Row {row.idx}: From Date {getdate(row.from_date)} cannot be before the last "
            f"Asset Movement {last.name} ({getdate(last.transaction_date)}) of this asset."
        )


# def _create_assignment_row_movements(doc):
#     """On adding a new assignment row: if the parent's project/location differ from the
#     asset's, create the Asset Movement dated with the row's from_date and link it."""
#     previous_doc = doc.get_doc_before_save()
#     old_names = {
#         r.name
#         for r in (previous_doc.get("custom_asset_assignment") if previous_doc else None) or []
#     }

#     new_rows = [
#         r for r in doc.get("custom_asset_assignment") or []
#         if r.name not in old_names
#     ]
#     if not new_rows:
#         return

#     row = new_rows[0]  # validate guarantees only one

#     movement_name = _create_asset_transfer(
#         doc, doc.asset, doc.get("project"), doc.get("department"),
#         submit=True,
#         target_location=doc.get("location"),
#         transaction_date=row.get("from_date"),
#         initial_assignment=not previous_doc,
#     )

#     if movement_name:
#         frappe.db.set_value(
#             row.doctype, row.name, "custom_asset_movement", movement_name,
#             update_modified=False,
#         )
#         row.custom_asset_movement = movement_name

def _create_assignment_row_movements(doc):
    """On adding a new assignment row: compare the row's project/location with the
    asset's, create the Asset Movement dated with the row's from_date and link it,
    then copy the row's project/location to the parent."""
    previous_doc = doc.get_doc_before_save()
    old_names = {
        r.name
        for r in (previous_doc.get("custom_asset_assignment") if previous_doc else None) or []
    }

    new_rows = [
        r for r in doc.get("custom_asset_assignment") or []
        if r.name not in old_names
    ]
    if not new_rows:
        return

    row = new_rows[0]  # validate guarantees only one
    project = row.get("project")
    location = row.get("location")

    if project or location:
        movement_name = _create_asset_transfer(
            doc, doc.asset, project,
            row.get("department") or doc.get("department"),
            submit=True,
            target_location=location,
            transaction_date=row.get("from_date"),
        )

        if movement_name:
            frappe.db.set_value(
                row.doctype, row.name, "custom_asset_movement", movement_name,
                update_modified=False,
            )
            row.custom_asset_movement = movement_name

    # parent mirrors the latest row (only the values the row actually has)
    for fieldname, value in (("project", project), ("location", location)):
        if value:
            doc.set(fieldname, value)
            frappe.db.set_value(
                doc.doctype, doc.name, fieldname, value, update_modified=False
            )

def set_target_project(doc, method=None):
    if doc.purpose == "Receipt":
        for row in doc.assets:
            if row.asset and not row.custom_target_project:
                row.custom_target_project = frappe.db.get_value("Asset", row.asset, "custom_project")
    for row in doc.assets:
        if row.asset and not row.department:
            row.department = frappe.db.get_value("Asset", row.asset, "department")

def update_asset_project(doc, method=None):
    """Asset Movement on_submit / on_cancel: refresh the asset's project, department
    and location from its latest submitted movement."""
    for row in doc.assets:
        if not row.asset:
            continue

        project = get_asset_project(row.asset)
        if project:
            frappe.db.set_value("Asset", row.asset, "custom_project", project, update_modified=False)

        department = get_asset_department(row.asset)
        if department:
            frappe.db.set_value("Asset", row.asset, "department", department, update_modified=False)

        # same-day movements tie on transaction_date (it is a Date field), so the
        # creation time breaks the tie
        location = frappe.db.sql(
            """
            SELECT ami.target_location
            FROM `tabAsset Movement Item` ami
            JOIN `tabAsset Movement` am ON ami.parent = am.name
            WHERE ami.asset = %s AND am.docstatus = 1
                AND IFNULL(ami.target_location, '') != ''
            ORDER BY am.transaction_date DESC, am.creation DESC
            LIMIT 1
            """,
            row.asset,
        )
        if location:
            frappe.db.set_value("Asset", row.asset, "location", location[0][0], update_modified=False)

# ---------------------------------------------------------------------------
# Locked assignment rows (IT Asset Management -> custom_asset_assignment)
# ---------------------------------------------------------------------------

ASSIGNMENT_CHILD_DOCTYPE = "IT Asset Assigned User2"

LOCKED_ROW_FIELDS = [
    "assigned_user", "department", "designation", "project",
    "location", "from_date", "to_date", "custom_asset_movement",
]


def _movement_is_active(movement_name):
    """True if the Asset Movement exists and is not cancelled."""
    if not movement_name:
        return False
    docstatus = frappe.db.get_value("Asset Movement", movement_name, "docstatus")
    return docstatus is not None and docstatus != 2


def validate_locked_assignment_rows(doc, method=None):
    """Block edits and deletes on rows linked to a non-cancelled Asset Movement."""
    previous_doc = doc.get_doc_before_save()
    if not previous_doc:
        return

    current_rows = {row.name: row for row in doc.get("custom_asset_assignment") or []}

    for old in previous_doc.get("custom_asset_assignment") or []:
        if not _movement_is_active(old.custom_asset_movement):
            continue

        new = current_rows.get(old.name)
        if not new:
            frappe.throw(
                f"Row {old.idx} is linked to Asset Movement {old.custom_asset_movement} "
                "and cannot be deleted. Cancel the movement first."
            )

        # the link is written server-side after save, so a stale client may send it empty;
        # restore it instead of treating it as an edit
        new.custom_asset_movement = old.custom_asset_movement

        for fieldname in LOCKED_ROW_FIELDS:
            if fieldname == "custom_asset_movement":
                continue
            if cstr(old.get(fieldname)) != cstr(new.get(fieldname)):
                frappe.throw(
                    f"Row {old.idx} is linked to Asset Movement {old.custom_asset_movement} "
                    "and cannot be edited. Cancel the movement first."
                )


def clear_assignment_link_on_cancel(doc, method=None):
    """Asset Movement on_cancel: unlink assignment rows so they become editable again,
    then reset each affected parent to its latest remaining active row."""
    rows = frappe.get_all(
        ASSIGNMENT_CHILD_DOCTYPE,
        filters={"custom_asset_movement": doc.name},
        fields=["name", "parent"],
    )
    parents = set()
    for r in rows:
        frappe.db.set_value(
            ASSIGNMENT_CHILD_DOCTYPE, r.name, "custom_asset_movement", None,
            update_modified=False,
        )
        parents.add(r.parent)

    for parent in parents:
        _sync_parent_from_latest_row(parent)


def _sync_parent_from_latest_row(parent_name):
    """Set the IT Asset Management project/location from its latest row that still
    has a non-cancelled movement."""
    remaining = frappe.get_all(
        ASSIGNMENT_CHILD_DOCTYPE,
        filters={"parent": parent_name, "parenttype": "IT Asset Management"},
        fields=["project", "location", "custom_asset_movement"],
        order_by="from_date desc, idx desc",
    )
    for r in remaining:
        if not _movement_is_active(r.custom_asset_movement):
            continue
        for fieldname in ("project", "location"):
            frappe.db.set_value(
                "IT Asset Management", parent_name, fieldname,
                r.get(fieldname) or None, update_modified=False,
            )
        return
# ---------------------------------------------------------------------------
# Movement creation
# ---------------------------------------------------------------------------
def create_asset_movement(doc, method=None):
    """Create a project/location transfer after an asset-linked record changes."""
    if not doc.asset:
        return

    # IT Asset Management: one movement per assignment row
    if doc.doctype == "IT Asset Management":
        _create_assignment_row_movements(doc)
        return

    previous_doc = doc.get_doc_before_save()
    project = doc.get("project")
    location = doc.get("location")

    if previous_doc and (
        previous_doc.get("project") == project
        and previous_doc.get("location") == location
    ):
        return

    if not project and not location and not previous_doc:
        return

    _create_asset_transfer(
        doc, doc.asset, project, doc.get("department"),
        initial_assignment=not previous_doc,
        target_location=location,
    )

def _get_active_movement(doc, asset, project=None, location=None):
    """Latest non-cancelled Transfer for this asset raised from this doc,
    matching the given target project and/or target location."""
    conditions = ""
    values = [doc.doctype, doc.name, asset]

    if project:
        conditions += " AND ami.custom_target_project = %s"
        values.append(project)
    if location:
        conditions += " AND ami.target_location = %s"
        values.append(location)

    if not conditions:
        return None

    result = frappe.db.sql(
        f"""
        SELECT am.name
        FROM `tabAsset Movement` am
        INNER JOIN `tabAsset Movement Item` ami ON ami.parent = am.name
        WHERE am.docstatus != 2
            AND am.purpose = 'Transfer'
            AND am.reference_doctype = %s
            AND am.reference_name = %s
            AND ami.asset = %s
            {conditions}
        ORDER BY am.creation DESC
        LIMIT 1
        """,
        tuple(values),
    )
    return result[0][0] if result else None

def _link_movements_to_assignment(doc):
    """For each assignment row without an active movement, link the active movement matching its project."""
    rows = doc.get("custom_asset_assignment") or []

    # movements already claimed by another row, so one movement isn't linked twice
    used = {
        r.get("custom_asset_movement")
        for r in rows
        if _movement_is_active(r.get("custom_asset_movement"))
    }

    for row in rows:
        if not (row.get("project") or row.get("location")):
            continue
        if _movement_is_active(row.get("custom_asset_movement")):
            continue

        movement_name = _get_active_movement(
            doc, doc.asset, row.get("project"), row.get("location")
        )
        if not movement_name or movement_name in used:
            continue

        frappe.db.set_value(
            row.doctype, row.name, "custom_asset_movement", movement_name,
            update_modified=False,
        )
        row.custom_asset_movement = movement_name
        used.add(movement_name)


def create_asset_movement_on_submit(doc, method=None):
    """Driver History on_submit: create and submit a project transfer, then link it on the record."""
    # clear first: an amended copy inherits the old (cancelled) movement's name
    frappe.db.set_value(
        doc.doctype, doc.name, "custom_asset_movement", None, update_modified=False
    )
    doc.custom_asset_movement = None

    # if not doc.asset or not doc.project:
    #     return

    # movement_name = _create_project_transfer(
    #     doc, doc.asset, doc.project, doc.get("department"), submit=True
    # )

    location = doc.get("location")
    if not doc.asset or not (doc.project or location):
        return

    movement_name = _create_asset_transfer(
        doc, doc.asset, doc.project, doc.get("department"),
        submit=True, target_location=location,
        transaction_date=doc.get("start_date"),
    )

    if movement_name:
        # db write because the Driver History is already submitted
        frappe.db.set_value(
            doc.doctype, doc.name, "custom_asset_movement", movement_name,
            update_modified=False,
        )
        doc.custom_asset_movement = movement_name


CANCEL_ALL_CMD = "frappe.desk.form.linked_with.cancel_all_linked_docs"


def _cancel_all_batch():
    """Documents listed in the current "Cancel All Documents" request, as {(doctype, name)}.

    That request cancels the *linked* documents of the one you pressed Cancel on (the
    document itself is excluded). Returns None when the request is something else.
    """
    if frappe.form_dict.get("cmd") != CANCEL_ALL_CMD:
        return None

    docs = frappe.form_dict.get("docs") or []
    if isinstance(docs, str):
        try:
            docs = json.loads(docs)
        except ValueError:
            return set()
    return {(d.get("doctype"), d.get("name")) for d in docs if isinstance(d, dict)}


def cancel_asset_movements(doc, method=None):
    """Driver History / Equipment Log Register before_cancel: cancel its submitted movements
    and remove its drafts.

    Runs before Frappe's linked-document check, which would otherwise block the cancel
    because the Asset Movement points back to this record.
    """
    movements = frappe.get_all(
        "Asset Movement",
        filters={
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "docstatus": ["in", [0, 1]],
        },
        fields=["name", "docstatus"],
    )

    # "Cancel All Documents" started from an Asset Movement would cancel this Driver History
    # as a linked doc; a movement must never cancel its Driver History
    batch = _cancel_all_batch()
    if batch is not None:
        submitted = [m.name for m in movements if m.docstatus == 1]
        if submitted and not any(("Asset Movement", n) in batch for n in submitted):
            frappe.throw(
                f"{doc.doctype} {doc.name} cannot be cancelled from an Asset Movement. "
                f"Cancel the {doc.doctype} directly."
            )

    # request-wide marker read by block_movement_cancel_if_source_submitted
    frappe.flags.cancelling_movement_source = (doc.doctype, doc.name)
    try:
        for m in movements:
            if m.docstatus == 1:
                movement = frappe.get_doc("Asset Movement", m.name)
                movement.flags.ignore_permissions = True
                movement.flags.from_source_cancel = True
                # the Driver History is still submitted and links to the movement at this
                # point, which would trip Frappe's linked-document check
                movement.flags.ignore_links = True
                movement.cancel()
            else:
                frappe.delete_doc("Asset Movement", m.name, ignore_permissions=True)
    finally:
        frappe.flags.cancelling_movement_source = None


# submittable doctypes that own the movements they create
SUBMITTABLE_MOVEMENT_SOURCES = ("Driver History", "Equipment Log Register")


def block_movement_cancel_if_source_submitted(doc, method=None):
    """Asset Movement before_cancel: a movement owned by a submitted Driver History or
    Equipment Log Register can only be cancelled by cancelling that document.

    Cancelling a movement never cancels or edits its source document.
    """
    source_doctype = doc.get("reference_doctype")
    source_name = doc.get("reference_name")
    if source_doctype not in SUBMITTABLE_MOVEMENT_SOURCES or not source_name:
        return

    if doc.flags.get("from_source_cancel"):
        return
    if frappe.flags.get("cancelling_movement_source") == (source_doctype, source_name):
        return

    if frappe.db.get_value(source_doctype, source_name, "docstatus") != 1:
        return

    batch = _cancel_all_batch()
    if batch is not None and (source_doctype, source_name) not in batch:
        # "Cancel All Documents" started from the source document: it cancels this movement
        # first and then the source itself. The submitted source still links to the movement,
        # so skip Frappe's linked-document check for this cancel.
        doc.flags.ignore_links = True
        return

    frappe.throw(
        f"Asset Movement {doc.name} belongs to submitted {source_doctype} "
        f"{source_name}. Cancel the {source_doctype} to cancel this movement."
    )


# old name, kept so existing hooks.py entries keep working
block_movement_cancel_if_driver_history_submitted = block_movement_cancel_if_source_submitted


def create_equipment_log_movements(doc, method=None):
    """Equipment Log Register on_submit: one submitted transfer per row with an asset and a
    project, linked back on the row in `asset_movement`."""
    for row in doc.equipment_log_item:
        # clear first: an amended copy inherits the old (cancelled) movement names
        frappe.db.set_value(
            row.doctype, row.name, "asset_movement", None, update_modified=False
        )
        row.asset_movement = None

        # if not row.asset or not row.project:
        #     continue

        # movement_name = _create_project_transfer(
        #     doc, row.asset, row.project, submit=True
        # )

        location = row.get("location")
        if not row.asset or not (row.project or location):
            continue

        movement_name = _create_asset_transfer(
            doc, row.asset, row.project,
            submit=True, target_location=location,
            transaction_date=row.get("from_date"),
        )


        if movement_name:
            # db write because the Equipment Log Register is already submitted
            frappe.db.set_value(
                row.doctype, row.name, "asset_movement", movement_name,
                update_modified=False,
            )
            row.asset_movement = movement_name

def _create_asset_transfer(
    doc, asset_name, target_project=None, department=None,
    initial_assignment=False, submit=False, target_location=None,
    transaction_date=None, force=False,
):
    # IT Asset Management always submits its movement; others only when asked (e.g. on submit)
    should_submit = submit or doc.doctype == "IT Asset Management"

    asset = frappe.db.get_value(
        "Asset", asset_name, ["custom_project", "company", "location", "department"], as_dict=True
    )
    if not asset:
        return

    project_changed = bool(target_project) and asset.custom_project != target_project
    location_changed = bool(target_location) and asset.location != target_location

    # first assignment never overrides a value the asset already has
    if initial_assignment:
        if asset.custom_project:
            project_changed = False
        if asset.location:
            location_changed = False

    draft = _get_draft_project_transfer(doc, asset_name, asset)

    if not (project_changed or location_changed) and not force:
        if draft:
            frappe.delete_doc("Asset Movement", draft.name, ignore_permissions=True)
        return

    # a movement cannot be dated before the asset's latest submitted movement
    move_date = getdate(transaction_date) if transaction_date else getdate(today())
    latest = _get_latest_movement(asset_name)
    if latest and getdate(latest.transaction_date) > move_date:
        frappe.throw(
            f"Asset {asset_name} already has Asset Movement {latest.name} dated "
            f"{getdate(latest.transaction_date)}, which is after {move_date}. "
            "Cancel it first or use a later date."
        )

    final_project = target_project if project_changed else asset.custom_project
    final_location = target_location if location_changed else asset.location

    if draft:
        row = draft.assets[0]
        row.custom_target_project = final_project
        row.target_location = final_location
        row.department = department or asset.department
        if transaction_date:
            draft.transaction_date = move_date
        draft.save(ignore_permissions=True)
        if should_submit:
            draft.flags.ignore_permissions = True
            draft.submit()
        frappe.msgprint(f"Asset Movement {draft.name} updated for asset {asset_name}.")
        return draft.name

    movement = frappe.new_doc("Asset Movement")
    movement.purpose = "Transfer"
    movement.company = asset.company
    movement.reference_doctype = doc.doctype
    movement.reference_name = doc.name
    movement.transaction_date = move_date
    movement.append("assets", {
        "asset": asset_name,
        "source_location": asset.location,
        "target_location": final_location,
        "custom_source_project": asset.custom_project or final_project,
        "custom_target_project": final_project,
        "department": department or asset.department,
    })

    movement.insert(ignore_permissions=True)

    if should_submit:
        movement.flags.ignore_permissions = True
        movement.submit()

    frappe.msgprint(f"Asset Movement {movement.name} created for asset {asset_name}.")
    return movement.name

# old name, kept so any other callers keep working
_create_project_transfer = _create_asset_transfer

def _get_draft_project_transfer(doc, asset_name, asset):
    drafts = frappe.get_all(
        "Asset Movement",
        filters={
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "purpose": "Transfer",
            "docstatus": 0,
        },
        pluck="name",
        order_by="creation desc",
    )
    for name in drafts:
        movement = frappe.get_doc("Asset Movement", name)
        if len(movement.assets) != 1:
            continue

        row = movement.assets[0]
        if (
            row.asset == asset_name
            and (not asset.custom_project or row.custom_source_project == asset.custom_project)
            # and row.source_location == row.target_location == asset.location
            and row.source_location == asset.location
        ):
            return movement


# def _create_project_transfer(
#     doc, asset_name, target_project, department=None, initial_assignment=False, submit=False
# ):
#     # IT Asset Management always submits its movement; others only when asked (e.g. on submit)
#     should_submit = submit or doc.doctype == "IT Asset Management"

#     asset = frappe.db.get_value(
#         "Asset", asset_name, ["custom_project", "company", "location", "department"], as_dict=True
#     )
#     if not asset:
#         return

#     draft = _get_draft_project_transfer(doc, asset_name, asset)
#     if not target_project or (asset.custom_project and asset.custom_project == target_project):
#         if draft:
#             frappe.delete_doc("Asset Movement", draft.name, ignore_permissions=True)
#         return

#     if draft:
#         row = draft.assets[0]
#         row.custom_target_project = target_project
#         row.department = department or asset.department
#         draft.save(ignore_permissions=True)
#         if should_submit:
#             draft.flags.ignore_permissions = True
#             draft.submit()
#         frappe.msgprint(f"Asset Movement {draft.name} updated for asset {asset_name}.")
#         return draft.name

#     if initial_assignment and asset.custom_project:
#         return

#     movement = frappe.new_doc("Asset Movement")
#     movement.purpose = "Transfer"
#     movement.company = asset.company
#     movement.reference_doctype = doc.doctype
#     movement.reference_name = doc.name

#     movement.append("assets", {
#         "asset": asset_name,
#         "source_location": asset.location,
#         "target_location": asset.location,
#         "custom_source_project": asset.custom_project or target_project,
#         "custom_target_project": target_project,
#         "department": department or asset.department,
#     })

#     movement.insert(ignore_permissions=True)

#     if should_submit:
#         movement.flags.ignore_permissions = True
#         movement.submit()

#     frappe.msgprint(
#         f"Asset Movement {movement.name} created for asset {asset_name}."
#     )
#     return movement.name

# def _create_asset_transfer(
#     doc, asset_name, target_project=None, department=None,
#     initial_assignment=False, submit=False, target_location=None,
#     transaction_date=None, force=False,
# ):
#     # IT Asset Management always submits its movement; others only when asked (e.g. on submit)
#     should_submit = submit or doc.doctype == "IT Asset Management"

#     asset = frappe.db.get_value(
#         "Asset", asset_name, ["custom_project", "company", "location", "department"], as_dict=True
#     )
#     if not asset:
#         return

#     project_changed = bool(target_project) and asset.custom_project != target_project
#     location_changed = bool(target_location) and asset.location != target_location

#     # first assignment never overrides a value the asset already has
#     if initial_assignment:
#         if asset.custom_project:
#             project_changed = False
#         if asset.location:
#             location_changed = False

#     draft = _get_draft_project_transfer(doc, asset_name, asset)

#     if not (project_changed or location_changed) and not force:
#         if draft:
#             frappe.delete_doc("Asset Movement", draft.name, ignore_permissions=True)
#         return

#     final_project = target_project if project_changed else asset.custom_project
#     final_location = target_location if location_changed else asset.location

#     if draft:
#         row = draft.assets[0]
#         row.custom_target_project = final_project
#         row.target_location = final_location
#         row.department = department or asset.department
#         if transaction_date:
#             draft.transaction_date = getdate(transaction_date)
#         draft.save(ignore_permissions=True)
#         if should_submit:
#             draft.flags.ignore_permissions = True
#             draft.submit()
#         frappe.msgprint(f"Asset Movement {draft.name} updated for asset {asset_name}.")
#         return draft.name

#     movement = frappe.new_doc("Asset Movement")
#     movement.purpose = "Transfer"
#     movement.company = asset.company
#     movement.reference_doctype = doc.doctype
#     movement.reference_name = doc.name
#     movement.transaction_date = getdate(transaction_date) if transaction_date else getdate(today())
#     movement.append("assets", {
#         "asset": asset_name,
#         "source_location": asset.location,
#         "target_location": final_location,
#         "custom_source_project": asset.custom_project or final_project,
#         "custom_target_project": final_project,
#         "department": department or asset.department,
#     })

#     movement.insert(ignore_permissions=True)

#     if should_submit:
#         movement.flags.ignore_permissions = True
#         movement.submit()

#     frappe.msgprint(f"Asset Movement {movement.name} created for asset {asset_name}.")
#     return movement.name


# def create_asset_movement(doc, method=None):
#     """Create a project transfer after an asset-linked record changes project."""
#     previous_doc = doc.get_doc_before_save()
#     if not doc.asset:
#         return

#     # if previous_doc and previous_doc.project == doc.project:
#     #     return

#     # if not doc.project and not previous_doc:
#     #     return

#     # _create_project_transfer(
#     #     doc, doc.asset, doc.project, doc.get("department"), initial_assignment=not previous_doc
#     # )
    
#     project = doc.get("project")
#     location = doc.get("location")

#     if previous_doc and (
#         previous_doc.get("project") == project
#         and previous_doc.get("location") == location
#     ):
#         return

#     if not project and not location and not previous_doc:
#         return

#     _create_asset_transfer(
#         doc, doc.asset, project, doc.get("department"),
#         initial_assignment=not previous_doc,
#         target_location=location,
#     )

#     if doc.doctype == "IT Asset Management":
#         _link_movements_to_assignment(doc)


# def _get_active_movement_for_project(doc, asset, project):
#     """Latest non-cancelled Transfer for this asset, targeting this project, raised from this doc."""
#     result = frappe.db.sql(
#         """
#         SELECT am.name
#         FROM `tabAsset Movement` am
#         INNER JOIN `tabAsset Movement Item` ami ON ami.parent = am.name
#         WHERE am.docstatus != 2
#             AND am.purpose = 'Transfer'
#             AND am.reference_doctype = %s
#             AND am.reference_name = %s
#             AND ami.asset = %s
#             AND ami.custom_target_project = %s
#         ORDER BY am.creation DESC
#         LIMIT 1
#         """,
#         (doc.doctype, doc.name, asset, project),
#     )
#     return result[0][0] if result else None


# def update_asset_project(doc, method=None):
#     for row in doc.assets:
#         if not row.asset:
#             continue
#         project = get_asset_project(row.asset)
#         if project:
#             frappe.db.set_value("Asset", row.asset, "custom_project", project, update_modified=False)
#         department = get_asset_department(row.asset)
#         if department:
#             frappe.db.set_value("Asset", row.asset, "department", department, update_modified=False)


# def validate_location_locked(doc, method=None):
#     """IT Asset Management validate: Location cannot be changed while a
#     non-cancelled Asset Movement raised from this record exists."""
#     previous_doc = doc.get_doc_before_save()
#     if not previous_doc:
#         return

#     if cstr(previous_doc.get("location")) == cstr(doc.get("location")):
#         return

#     movement = frappe.db.get_value(
#         "Asset Movement",
#         {
#             "reference_doctype": doc.doctype,
#             "reference_name": doc.name,
#             "docstatus": ["!=", 2],
#         },
#         "name",
#     )
#     if movement:
#         frappe.throw(
#             f"Location cannot be changed because Asset Movement {movement} is already "
#             "linked to this record. Cancel the movement first."
#         )


# def validate_single_new_assignment_row(doc, method=None):
#     """IT Asset Management validate: one new assignment row per save, and its
#     from_date cannot be earlier than the asset's last movement."""
#     previous_doc = doc.get_doc_before_save()
#     old_names = {
#         r.name
#         for r in (previous_doc.get("custom_asset_assignment") if previous_doc else None) or []
#     }

#     new_rows = [
#         r for r in doc.get("custom_asset_assignment") or []
#         if r.name not in old_names
#     ]

#     if len(new_rows) > 1:
#         frappe.throw(
#             "Please add only one Asset Assignment row at a time. "
#             f"You added {len(new_rows)} rows (#{', #'.join(str(r.idx) for r in new_rows)}). "
#             "Save after each row."
#         )

#     # if not new_rows or not doc.asset:
#     #     return

#     # row = new_rows[0]
#     # if not (row.get("project") or row.get("location")) or not row.get("from_date"):
#     #     return

#     # last = _get_last_movement(doc.asset)
#     # if last and getdate(row.from_date) < getdate(last.transaction_date):
#     #     frappe.throw(
#     #         f"Row {row.idx}: From Date {getdate(row.from_date)} cannot be before the last "
#     #         f"Asset Movement {last.name} ({getdate(last.transaction_date)}) of this asset."
#     #     )

#     if not new_rows or not doc.asset:
#         return

#     row = new_rows[0]
#     if not row.get("from_date"):
#         return

#     last = _get_last_movement(doc)
#     if last and getdate(row.from_date) < getdate(last.transaction_date):
#         frappe.throw(
#             f"Row {row.idx}: From Date {getdate(row.from_date)} cannot be before the last "
#             f"Asset Movement {last.name} ({getdate(last.transaction_date)}) of this asset."
#         )


# def validate_single_new_assignment_row(doc, method=None):
#     """IT Asset Management validate: only one new assignment row can be added per save."""
#     previous_doc = doc.get_doc_before_save()
#     old_names = {
#         r.name
#         for r in (previous_doc.get("custom_asset_assignment") if previous_doc else None) or []
#     }

#     new_rows = [
#         r for r in doc.get("custom_asset_assignment") or []
#         if r.name not in old_names
#     ]

#     if len(new_rows) > 1:
#         frappe.throw(
#             "Please add only one Asset Assignment row at a time. "
#             f"You added {len(new_rows)} rows (#{', #'.join(str(r.idx) for r in new_rows)}). "
#             "Save after each row."
#         )


# def _create_assignment_row_movements(doc):
#     """Create the Asset Movement for the one new assignment row and link it."""
#     for row in _rows_needing_movement(doc):
#         movement_name = _create_asset_transfer(
#             doc, doc.asset, row.get("project"),
#             row.get("department") or doc.get("department"),
#             submit=True,
#             target_location=row.get("location"),
#             transaction_date=row.get("from_date"),
#         )

#         if movement_name:
#             frappe.db.set_value(
#                 row.doctype, row.name, "custom_asset_movement", movement_name,
#                 update_modified=False,
#             )
#             row.custom_asset_movement = movement_name

# def _get_last_movement(doc):
#     """Latest submitted Asset Movement raised from this record for its asset."""
#     result = frappe.db.sql(
#         """
#         SELECT am.name, am.transaction_date
#         FROM `tabAsset Movement` am
#         INNER JOIN `tabAsset Movement Item` ami ON ami.parent = am.name
#         WHERE am.docstatus = 1
#             AND am.reference_doctype = %s
#             AND am.reference_name = %s
#             AND ami.asset = %s
#         ORDER BY am.transaction_date DESC, am.creation DESC
#         LIMIT 1
#         """,
#         (doc.doctype, doc.name, doc.asset),
#         as_dict=True,
#     )
#     return result[0] if result else None

##############################################################################################################
# import frappe
# from mkan_customization.mkan_customization.override.asset import get_asset_project, get_asset_department
# from frappe.utils import cstr


# def set_target_project(doc, method=None):
#     if doc.purpose == "Receipt":
#         for row in doc.assets:
#             if row.asset and not row.custom_target_project:
#                 row.custom_target_project = frappe.db.get_value("Asset", row.asset, "custom_project")
#     for row in doc.assets:
#         if row.asset and not row.department:
#             row.department = frappe.db.get_value("Asset", row.asset, "department")

# def update_asset_project(doc, method=None):
#     for row in doc.assets:
#         if not row.asset:
#             continue
#         project = get_asset_project(row.asset)
#         if project:
#             frappe.db.set_value("Asset", row.asset, "custom_project", project, update_modified=False)
#         department = get_asset_department(row.asset)
#         if department:
#             frappe.db.set_value("Asset", row.asset, "department", department, update_modified=False)

# LOCKED_ROW_FIELDS = [
#     "assigned_user", "department", "designation", "project",
#     "location", "from_date", "to_date", "custom_asset_movement",
# ]


# def _movement_is_active(movement_name):
#     """True if the Asset Movement exists and is not cancelled."""
#     if not movement_name:
#         return False
#     docstatus = frappe.db.get_value("Asset Movement", movement_name, "docstatus")
#     return docstatus is not None and docstatus != 2


# def validate_locked_assignment_rows(doc, method=None):
#     """Block edits and deletes on rows linked to a non-cancelled Asset Movement."""
#     previous_doc = doc.get_doc_before_save()
#     if not previous_doc:
#         return

#     current_rows = {row.name: row for row in doc.get("custom_asset_assignment") or []}

#     for old in previous_doc.get("custom_asset_assignment") or []:
#         if not _movement_is_active(old.custom_asset_movement):
#             continue

#         new = current_rows.get(old.name)
#         if not new:
#             frappe.throw(
#                 f"Row {old.idx} is linked to Asset Movement {old.custom_asset_movement} "
#                 "and cannot be deleted. Cancel the movement first."
#             )

#         for fieldname in LOCKED_ROW_FIELDS:
#             if cstr(old.get(fieldname)) != cstr(new.get(fieldname)):
#                 frappe.throw(
#                     f"Row {old.idx} is linked to Asset Movement {old.custom_asset_movement} "
#                     "and cannot be edited. Cancel the movement first."
#                 )

# # def create_asset_movement(doc, method=None):
# #     """Create a project transfer after an asset-linked record changes project."""
# #     previous_doc = doc.get_doc_before_save()
# #     if not doc.asset:
# #         return

# #     if previous_doc and previous_doc.project == doc.project:
# #         return

# #     if not doc.project and not previous_doc:
# #         return

# #     _create_project_transfer(
# #         doc, doc.asset, doc.project, doc.get("department"), initial_assignment=not previous_doc
# #     )

# def create_asset_movement(doc, method=None):
#     """Create a project transfer after an asset-linked record changes project."""
#     previous_doc = doc.get_doc_before_save()
#     if not doc.asset:
#         return

#     if previous_doc and previous_doc.project == doc.project:
#         return

#     if not doc.project and not previous_doc:
#         return

#     movement_name = _create_project_transfer(
#         doc, doc.asset, doc.project, doc.get("department"), initial_assignment=not previous_doc
#     )

#     if movement_name and doc.doctype == "IT Asset Management":
#         _link_movement_to_assignment(doc, movement_name)


# def _link_movement_to_assignment(doc, movement_name):
#     for row in doc.get("custom_asset_assignment") or []:
#         if row.get("project") == doc.project and not _movement_is_active(row.get("custom_asset_movement")):
#             frappe.db.set_value(
#                 row.doctype, row.name, "custom_asset_movement", movement_name,
#                 update_modified=False,
#             )
#             row.custom_asset_movement = movement_name
            


# def create_equipment_log_movements(doc, method=None):
#     """Create one transfer for each equipment row whose project changed."""
#     previous_doc = doc.get_doc_before_save()
#     previous_rows = {row.name: row for row in previous_doc.equipment_log_item} if previous_doc else {}
#     for row in doc.equipment_log_item:
#         previous_row = previous_rows.get(row.name)
#         if previous_row and previous_row.project == row.project:
#             continue

#         if row.asset and (row.project or previous_row):
#             _create_project_transfer(
#                 doc, row.asset, row.project, initial_assignment=not previous_row
#             )


# def _create_project_transfer(doc, asset_name, target_project, department=None, initial_assignment=False):
#     asset = frappe.db.get_value(
#         "Asset", asset_name, ["custom_project", "company", "location", "department"], as_dict=True
#     )
#     if not asset:
#         return

#     draft = _get_draft_project_transfer(doc, asset_name, asset)
#     if not target_project or (asset.custom_project and asset.custom_project == target_project):
#         if draft:
#             frappe.delete_doc("Asset Movement", draft.name, ignore_permissions=True)
#         return

#     if draft:
#         row = draft.assets[0]
#         row.custom_target_project = target_project
#         row.department = department or asset.department
#         draft.save(ignore_permissions=True)
#         frappe.msgprint(f"Asset Movement {draft.name} updated for asset {asset_name}.")
#         return

#     if initial_assignment and asset.custom_project:
#         return

#     movement = frappe.new_doc("Asset Movement")
#     movement.purpose = "Transfer"
#     movement.company = asset.company
#     movement.reference_doctype = doc.doctype
#     movement.reference_name = doc.name

#     movement.append("assets", {
#         "asset": asset_name,
#         "source_location": asset.location,
#         "target_location": asset.location,
#         "custom_source_project": asset.custom_project or target_project,
#         "custom_target_project": target_project,
#         "department": department or asset.department,
#     })

#     movement.insert(ignore_permissions=True)

#     if doc.doctype == "IT Asset Management":
#         movement.flags.ignore_permissions = True
#         movement.submit()

#     frappe.msgprint(
#         f"Asset Movement {movement.name} created for asset {asset_name}."
#     )
#     return movement.name 


# def _get_draft_project_transfer(doc, asset_name, asset):
#     drafts = frappe.get_all(
#         "Asset Movement",
#         filters={
#             "reference_doctype": doc.doctype,
#             "reference_name": doc.name,
#             "purpose": "Transfer",
#             "docstatus": 0,
#         },
#         pluck="name",
#         order_by="creation desc",
#     )
#     for name in drafts:
#         movement = frappe.get_doc("Asset Movement", name)
#         if len(movement.assets) != 1:
#             continue

#         row = movement.assets[0]
#         if (
#             row.asset == asset_name
#             and (not asset.custom_project or row.custom_source_project == asset.custom_project)
#             and row.source_location == row.target_location == asset.location
#         ):
#             return movement
