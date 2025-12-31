# Copyright (c) 2025, Finbyz and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase
import frappe
from datetime import timedelta
from frappe.utils import now_datetime, add_to_date
from mkan_customization.mkan_customization.doctype.helpdesk_request.helpdesk_request import check_and_close_timeout_tickets

class TestHelpdeskRequest(FrappeTestCase):
	def setUp(self):
		self.doc = frappe.get_doc({
			"doctype": "Helpdesk Request",
			"employee_id": frappe.get_all("Employee", limit=1)[0].name,
			"naming_series": "HDR-.YYYY.-"
		}).insert()

	def tearDown(self):
		self.doc.delete()

	def test_it_response_date_set_on_status_change(self):
		# Initial state should not have response date
		self.doc.reload()
		self.assertIsNone(self.doc.custom_it_response_date)

		# Change to Waiting for User Feedback
		self.doc.workflow_state = "Waiting for User Feedback"
		self.doc.save()
		
		self.doc.reload()
		date1 = self.doc.custom_it_response_date
		self.assertIsNotNone(date1)

		# Change another field, date should NOT change
		self.doc.project = frappe.get_all("Project", limit=1)[0].name
		self.doc.save()
		
		self.doc.reload()
		date2 = self.doc.custom_it_response_date
		self.assertEqual(date1, date2)

	def test_auto_close_tickets(self):
		# Set to Waiting for User Feedback
		self.doc.workflow_state = "Waiting for User Feedback"
		self.doc.save()
		
		# Manually set the date to 3 days ago
		three_days_ago = now_datetime() - timedelta(days=3)
		frappe.db.set_value("Helpdesk Request", self.doc.name, "custom_it_response_date", three_days_ago)
		
		# Run the auto-close function
		closed_count = check_and_close_timeout_tickets()
		
		# Verify ticket is closed
		self.doc.reload()
		self.assertEqual(self.doc.workflow_state, "Closed")
		self.assertIsNotNone(self.doc.custom_closed_ticket_date)
		
		# Verify comment was added
		comments = frappe.get_all("Comment", filters={"reference_doctype": "Helpdesk Request", "reference_name": self.doc.name})
		self.assertTrue(any("automatically closed" in c.content for c in comments))
