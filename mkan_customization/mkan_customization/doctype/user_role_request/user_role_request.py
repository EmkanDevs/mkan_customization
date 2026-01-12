import frappe
import json
from frappe import _
from frappe.model.document import Document
from mkan_customization.mkan_customization.override import assign_to
from frappe.utils import get_fullname, get_url_to_form

class UserRoleRequest(Document):
	def before_save(self):
		self.handle_workflow_notifications()
		self.handle_auto_approvals()
		self.auto_assign_role_owners()

	def on_submit(self):
		if self.workflow_state == "Approve by System Manager":
			self._auto_share_with_role_owners()

	def on_update_after_submit(self):
		if self.workflow_state == "Approve by System Manager":
			self._auto_share_with_role_owners()

	def _auto_share_with_role_owners(self):
		from mkan_customization.mkan_customization.doctype.user_role_request.user_role_request import (
			share_document_with_role_owners
		)
		share_document_with_role_owners(self.name)


	def handle_auto_approvals(self):
		# Approver level approval - mark as approved when moved to System Manager approval state
		if self.workflow_state == "Send for Approval (System Manager)":
			for row in self.role_request_details:
				if not row.approved:
					row.approved = 1

		# Final approval by System Manager - assign roles to user
		if self.workflow_state == "Approve by System Manager":
			for row in self.role_request_details:
				if row.approved and not row.system_manager_approved:
					row.system_manager_approved = 1
			# Assign roles to user
			self.assign_roles_to_user()

		# Rejection
		if self.workflow_state == "Rejected":
			for row in self.role_request_details:
				row.rejected = 1
				row.approved = 0
				row.system_manager_approved = 0

	def handle_workflow_notifications(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		# Send email when moved to Send for Approval
		if (
			doc_before_save.workflow_state != "Send for Approval"
			and self.workflow_state == "Send for Approval"
		):
			send_approval_email(self)

		# Send email when approved by approver and sent to System Manager
		if (
			doc_before_save.workflow_state != "Send for Approval (System Manager)"
			and self.workflow_state == "Send for Approval (System Manager)"
		):
			# Get approved roles
			approved_roles = [row.requested_role for row in self.role_request_details if row.approved]
			send_system_manager_approval_email(self, roles=approved_roles)

		# Send notification to role owners when finally approved
		if (
			doc_before_save.workflow_state != "Approve by System Manager"
			and self.workflow_state == "Approve by System Manager"
		):
			self.notify_role_owners()

	def auto_assign_role_owners(self):
		"""Automatically fetch and assign role owners when roles are added"""
		if not self.role_request_details:
			return
		
		for row in self.role_request_details:
			if row.requested_role and not row.role_owners:
				# Fetch role owners for this role
				owners = get_owners_for_role(row.requested_role)
				if owners:
					# Assign the first owner (or you can modify to assign all)
					row.role_owners = owners[0] if owners else ""

	def notify_role_owners(self):
		"""Notify role owners after final approval"""
		role_owners = {}
		for row in self.role_request_details:
			if row.system_manager_approved and row.role_owners and row.requested_role:
				if row.role_owners not in role_owners:
					role_owners[row.role_owners] = []
				role_owners[row.role_owners].append(row.requested_role)
		
		for owner, roles in role_owners.items():
			send_role_owner_notification(self, owner, roles)

	def assign_roles_to_user(self):
		"""Assign approved roles to the user"""
		if not self.user_id:
			return

		user = frappe.get_doc("User", self.user_id)
		existing_roles = {r.role for r in user.roles}
		
		roles_added = []
		for row in self.role_request_details:
			if row.system_manager_approved and row.requested_role and row.requested_role not in existing_roles:
				user.append("roles", {"role": row.requested_role})
				roles_added.append(row.requested_role)
		
		if roles_added:
			user.save(ignore_permissions=True)
			frappe.msgprint(_("Successfully added roles to {0}: {1}").format(self.user_id, ", ".join(roles_added)))

	def validate(self):
		self.validate_employee()


	def validate_employee(self):
		if not self.employee_id:
			employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
			if employee:
				self.employee_id = employee

@frappe.whitelist()
def send_approval_email(doc):
	if isinstance(doc, str):
		doc = json.loads(doc)
	
	doc = frappe.get_doc(doc)

	if not doc.approver:
		return

	requestor_name = frappe.utils.get_fullname(doc.owner)
	subject = _("Action Required: User Role Request for {0}").format(doc.employee_name)
	
	message = frappe.render_template("""
		<div style="font-family: Arial, sans-serif; color: #333;">
			<p>Dear Approver,</p>
			
			<p>A new <b>User Role Request</b> has been submitted for your review and approval.</p>

			<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; width: 150px; font-weight: bold;">Requested By:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ requestor_name }}</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Employee:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.employee_name }} ({{ doc.employee_id }})</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Department:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.department }}</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Designation:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.designation }}</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Priority:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.priority }}</td>
				</tr>
			</table>

			<p><b>Requested Roles:</b></p>
			<ul>
			{% for row in doc.role_request_details %}
				<li>{{ row.requested_role }}</li>
			{% endfor %}
			</ul>

			<br>
			<p>
				<a href="{{ link }}" style="display: inline-block; background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">
					👉 Review and Approve
				</a>
			</p>
			
			<br>
			<p style="font-size: 12px; color: #777;">This is an automated message. Please do not reply directly to this email.</p>
		</div>
	""", {
		"doc": doc,
		"requestor_name": requestor_name,
		"link": frappe.utils.get_url_to_form(doc.doctype, doc.name)
	})

	frappe.sendmail(
		recipients=doc.approver,
		subject=subject,
		message=message
	)

@frappe.whitelist()
def send_system_manager_approval_email(doc, **kwargs):
	if isinstance(doc, str):
		doc = json.loads(doc)

	if not isinstance(doc, Document):
		doc = frappe.get_doc(doc)

	# Get approved roles
	approved_roles = kwargs.get("roles", [])
	if not approved_roles:
		approved_roles = [row.requested_role for row in doc.role_request_details 
						 if row.approved and row.requested_role]

	if not approved_roles:
		return

	# Get all System Managers
	system_managers = frappe.get_all(
		"Has Role", 
		filters={"role": "System Manager", "parenttype": "User"}, 
		fields=["parent"]
	)
	
	recipients = [u.parent for u in system_managers if u.parent and u.parent != "Administrator"]

	if not recipients:
		return

	requestor_name = frappe.utils.get_fullname(doc.owner)
	project_name = doc.project if doc.project else "N/A"

	subject = _("Action Required: System Manager Approval for User Role Request {0}").format(doc.name)
	
	approved_roles_list = ""
	for role in approved_roles:
		approved_roles_list += f"<li>{role}</li>"
	
	message = frappe.render_template("""
		<div style="font-family: Arial, sans-serif; color: #333;">
			<p>Dear System Manager,</p>
			
			<p>A <b>User Role Request</b> has been approved by the Approver and now requires your final approval for the following roles:</p>

			<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; width: 150px; font-weight: bold;">Requested By:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ requestor_name }}</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Employee:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.employee_name }} ({{ doc.employee_id }})</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Project:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ project_name }}</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Priority:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.priority }}</td>
				</tr>
			</table>

			<p><b>Roles Pending Your Approval:</b></p>
			<ul>
				{{ approved_roles_list | safe }}
			</ul>

			<br>
			<p>
				<a href="{{ link }}" style="display: inline-block; background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">
					👉 Review and Grant Permissions
				</a>
			</p>
			
			<br>
			<p style="font-size: 12px; color: #777;">This is an automated message. Please do not reply directly to this email.</p>
		</div>
	""", {
		"doc": doc,
		"requestor_name": requestor_name,
		"project_name": project_name,
		"approved_roles_list": approved_roles_list,
		"link": frappe.utils.get_url_to_form(doc.doctype, doc.name)
	})

	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		message=message
	)

@frappe.whitelist()
def send_role_owner_notification(doc, role_owner, roles):
	"""Send notification to role owner after final approval"""
	if isinstance(doc, str):
		doc = json.loads(doc)
	
	doc = frappe.get_doc(doc)
	
	subject = _("Notification: New Roles Assigned to {0}").format(doc.employee_name)
	
	roles_list = ""
	for role in roles:
		roles_list += f"<li>{role}</li>"
	
	message = frappe.render_template("""
		<div style="font-family: Arial, sans-serif; color: #333;">
			<p>Dear Role Owner,</p>
			
			<p>The following roles have been assigned to <b>{{ doc.employee_name }}</b> and you have been designated as the role owner:</p>

			<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; width: 150px; font-weight: bold;">Employee:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.employee_name }} ({{ doc.employee_id }})</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Project:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.project }}</td>
				</tr>
				<tr>
					<td style="padding: 8px; border-bottom: 1px solid #ddd; font-weight: bold;">Department:</td>
					<td style="padding: 8px; border-bottom: 1px solid #ddd;">{{ doc.department }}</td>
				</tr>
			</table>

			<p><b>Roles Assigned:</b></p>
			<ul>
				{{ roles_list | safe }}
			</ul>

			<br>
			<p>
				<a href="{{ link }}" style="display: inline-block; background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">
					👉 View User Role Request
				</a>
			</p>
			
			<br>
			<p style="font-size: 12px; color: #777;">This is an automated message. Please do not reply directly to this email.</p>
		</div>
	""", {
		"doc": doc,
		"roles_list": roles_list,
		"link": frappe.utils.get_url_to_form(doc.doctype, doc.name)
	})

	frappe.sendmail(
		recipients=role_owner,
		subject=subject,
		message=message
	)

@frappe.whitelist()
def get_role_owners(roles):
	if isinstance(roles, str):
		roles = json.loads(roles)

	if not roles:
		return []

	role_allotment = frappe.get_doc("Role Allotment")
	
	owners = set()
	for row in role_allotment.role_owner_list:
		if row.role in roles and row.role_owners:
			for owner in row.role_owners.split(","):
				owner = owner.strip()
				if owner:
					owners.add(owner)

	if not owners:
		return []

	valid_owners = frappe.get_all(
		"Has Role",
		filters={
			"role": "Approver",
			"parent": ["in", list(owners)]
		},
		pluck="parent"
	)

	return valid_owners

@frappe.whitelist()
def get_owners_for_role(role):
	"""
	Fetch owners for a single role from the Single Doctype 'Role Allotment'.
	Returns a list of owner names.
	"""
	if not role:
		return []

	role_allotment = frappe.get_doc("Role Allotment")
	
	owners = []
	for row in role_allotment.role_owner_list:
		if row.role == role and row.role_owners:
			# Handle comma-separated role owners
			for owner in row.role_owners.split(","):
				owner = owner.strip()
				if owner and owner not in owners:
					owners.append(owner)

	# Filter to ensure owners also have the 'Approver' role
	if not owners:
		return []

	valid_owners = frappe.get_all(
		"Has Role",
		filters={
			"role": "Approver",
			"parent": ["in", owners]
		},
		pluck="parent"
	)

	return valid_owners



@frappe.whitelist()
def get_all_approvers():
	"""
	Fetch all users who have the 'Approver' role.
	"""
	approvers = frappe.get_all(
		"Has Role",
		filters={"role": "Approver"},
		pluck="parent"
	)
	return list(set(approvers))

@frappe.whitelist()
def fetch_role_owners_for_doc(docname):
	"""Fetch and assign role owners for all roles in the document"""
	doc = frappe.get_doc("User Role Request", docname)
	
	for row in doc.role_request_details:
		if row.requested_role and not row.role_owners:
			owners = get_owners_for_role(row.requested_role)
			if owners:
				row.role_owners = owners[0]  # Assign first owner
	
	doc.save(ignore_permissions=True)
	return True

@frappe.whitelist()
def share_document_with_role_owners(docname):
	"""Share the User Role Request document with all role owners after final approval"""
	doc = frappe.get_doc("User Role Request", docname)
	
	frappe.logger().info(f"Starting document sharing process for {docname}")
	frappe.logger().info(f"Current workflow state: {doc.workflow_state}")
	
	# Collect all unique role owners from approved roles
	role_owners = set()
	for row in doc.role_request_details:
		if (row.system_manager_approved or row.approved) and row.role_owners:
			for owner in row.role_owners.split(","):
				owner = owner.strip()
				if owner:
					role_owners.add(owner)
					frappe.logger().info(
						f"[AUTO-SHARE] {doc.name} | role={row.requested_role} | owner={owner} "
						f"| approved={row.approved} | sm={row.system_manager_approved}"
					)

	
	if not role_owners:
		frappe.logger().warning(f"No role owners found for document {docname}")
		frappe.logger().warning(f"Role request details: {[(r.requested_role, r.approved, r.role_owners) for r in doc.role_request_details]}")
		return False
	
	frappe.logger().info(f"Total unique role owners to share with: {len(role_owners)} - {list(role_owners)}")
	
	# Share document with each role owner
	shared_count = 0
	for owner in role_owners:
		# Verify the user exists
		if not frappe.db.exists("User", owner):
			frappe.logger().error(f"User {owner} does not exist, skipping")
			continue
			
		# Check if already shared
		existing_share = frappe.db.exists("DocShare", {
			"share_doctype": doc.doctype,
			"share_name": doc.name,
			"user": owner
		})
		
		if not existing_share:
			try:
				# Grant full permissions: read, write, and share
				frappe.share.add(
					doc.doctype,
					doc.name,
					owner,
					read=1,
					write=1,
					submit=1,
					share=0,
					notify=1
				)

				frappe.logger().info(f"✅ Successfully shared {doc.name} with {owner} (read, write, share)")
				shared_count += 1
			except Exception as e:
				frappe.logger().error(f"❌ Failed to share {doc.name} with {owner}: {str(e)}")
				import traceback
				frappe.logger().error(traceback.format_exc())
		else:
			frappe.logger().info(f"Document {doc.name} already shared with {owner}, skipping")
	
	frappe.db.commit()
	frappe.logger().info(f"Document sharing completed. Shared with {shared_count} new role owners")
	return shared_count > 0 or len(role_owners) > 0

@frappe.whitelist()
def close_request(docname):
	doc = frappe.get_doc("User Role Request", docname)
	doc.status = "Closed"
	doc.save(ignore_permissions=True)
	return True

@frappe.whitelist()
def debug_sharing_info(docname):
	"""Debug function to check why sharing might not be working"""
	doc = frappe.get_doc("User Role Request", docname)
	
	info = {
		"docname": docname,
		"workflow_state": doc.workflow_state,
		"role_details": []
	}
	
	for row in doc.role_request_details:
		info["role_details"].append({
			"requested_role": row.requested_role,
			"approved": row.approved,
			"system_manager_approved": row.system_manager_approved,
			"role_owners": row.role_owners,
			"rejected": row.rejected
		})
	
	# Check current shares
	existing_shares = frappe.get_all("DocShare", 
		filters={
			"share_doctype": doc.doctype,
			"share_name": doc.name
		},
		fields=["user", "read", "write", "share"]
	)
	
	info["existing_shares"] = existing_shares
	
	return info


