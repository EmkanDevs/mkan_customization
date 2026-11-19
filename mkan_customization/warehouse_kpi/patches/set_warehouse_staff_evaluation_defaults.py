import frappe
from mkan_customization.warehouse_kpi.doctype.warehouse_staff_evaluation_settings.warehouse_staff_evaluation_settings import (
	init_default_settings,
)


def execute():
	init_default_settings()
