import frappe
from erpnext.assets.doctype.asset_movement.asset_movement import AssetMovement as ERPNextAssetMovement


class AssetMovement(ERPNextAssetMovement):
    def validate_location(self, row):
        if self.is_project_only_transfer(row):
            return

        super().validate_location(row)

    def is_project_only_transfer(self, row):
        if (
            self.purpose != "Transfer"
            or self.reference_doctype not in (
                "IT Asset Management", "Driver History", "Equipment Log Register"
            )
            or not self.reference_name
            or not row.asset
            or not row.custom_source_project
            or not row.custom_target_project
        ):
            return False

        source = frappe.db.get_value(
            "Asset", row.asset, ["location", "custom_project"], as_dict=True
        )
        if self.reference_doctype == "Equipment Log Register":
            valid_reference = frappe.db.exists(
                "Equipment Log Item",
                {
                    "parent": self.reference_name,
                    "parenttype": self.reference_doctype,
                    "asset": row.asset,
                    "project": row.custom_target_project,
                },
            )
        else:
            reference = frappe.db.get_value(
                self.reference_doctype, self.reference_name, ["asset", "project"], as_dict=True
            )
            valid_reference = (
                reference
                and reference.asset == row.asset
                and reference.project == row.custom_target_project
            )

        return bool(
            source
            and valid_reference
            and row.source_location == row.target_location == source.location
            and (not source.custom_project or row.custom_source_project == source.custom_project)
        )
