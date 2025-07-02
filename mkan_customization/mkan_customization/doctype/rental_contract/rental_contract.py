# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime
from frappe.utils import getdate, today
from frappe.desk.form.load import get_attachments

class RentalContract(Document):
    pass

def send_rental_reminders_electric_and_water():
    today_date = getdate(today())
    day_of_month = today_date.day

    contracts = frappe.get_all(
        "Rental Contract",
        filters={
            "contract_is_active": 1
        },
        fields=[
            "name", "project_name", "location", "onwer_name", "onwer_contact_no",
            "monthly_reminder_day_elctric", "monthly_reminder_day_water",
            "start_of_contract", "note"
        ]
    )

    for contract in contracts:
        start_date = getdate(contract.start_of_contract)

        if today_date < start_date:
            continue  # Contract hasn't started yet

        # Email triggers
        if contract.monthly_reminder_day_elctric == day_of_month:
            send_email_reminder_electric_and_water(contract, "Electric")

        if contract.monthly_reminder_day_water == day_of_month:
            send_email_reminder_electric_and_water(contract, "Water")

def send_email_reminder_electric_and_water(contract, reminder_type):
    subject = f"{reminder_type} Reminder for {contract.project_name} - {contract.name}"
    message = f"""
    <p>Dear {contract.owner_name},</p>
    <p>This is a monthly reminder for your <strong>{reminder_type.lower()} utility</strong> as per your contract at <strong>{contract.location}</strong>.</p>
    <ul>
        <li><b>Contract:</b> {contract.name}</li>
        <li><b>Contract Type:</b> {contract.contract_type}</li>
        <li><b>Contract No:</b> {contract.contract_no}</li>
        <li><b>Start Date:</b> {contract.start_of_contract}</li>
        <li><b>End Date:</b> {contract.end_of_contract}</li>
        <li><b>Project:</b> {contract.project_name}</li>
        <li><b>Location:</b> {contract.location}</li>
        <li><b>Accommodation Type:</b> {contract.accommodation_type or "N/A"}</li>
        <li><b>Payment Frequency:</b> {contract.payment_frequency}</li>
        <li><b>Yearly Rent:</b> {contract.yearly_rent}</li>
    </ul>
    <p>Kindly take necessary actions.</p>
    <p>Regards,<br>Your Team</p>
    """
    attachment_file_names = get_attachments("Rental Contract",contract.name)
    frappe.sendmail(
        recipients=get_users_with_role("Public Relation Manager"),
        subject=subject,
        message=message,
        reference_doctype="Rental Contract",
        reference_name=contract.name,
        attachments=attachment_file_names # Pass the list of File DocType names here
    )

# Call the function if you're testing
# send_rental_reminders()
def get_users_with_role(role_name):
    """Return list of active users who have the given role."""
    
    # Get users from Has Role table
    users = frappe.get_all(
        "Has Role",
        filters={"role": role_name},
        fields=["parent"],
        distinct=True
    )

    user_ids = [u.parent for u in users]

    # Filter out disabled users
    active_users = frappe.get_all(
        "User",
        filters={"name": ["in", user_ids], "enabled": 1},
        pluck="name"
    )

    return active_users



def send_rent_payment_reminders():
    today_date = getdate(today())
    current_day = today_date.day
    current_month = today_date.month

    contracts = frappe.get_all(
        "Rental Contract",
        filters={"contract_is_active": 1},
        fields=["name", "project_name", "location", "onwer_name", "onwer_contact_no",
                "yearly_rent", "payment_frequency", "start_of_contract", "owner"]
    )

    for contract in contracts:
        rent_amount = 0
        should_send = False

        freq = contract.payment_frequency
        yearly_rent = contract.yearly_rent or 0

        if freq == "2" and current_day == 1:
            rent_amount = yearly_rent / 12
            should_send = True

        elif freq == "3 Months" and current_day == 1 and current_month in [1, 4, 7, 10]:
            rent_amount = yearly_rent / 4
            should_send = True

        elif freq == "6 Months" and current_day == 1 and current_month in [1, 7]:
            rent_amount = yearly_rent / 2
            should_send = True

        elif freq == "Yearly" and current_day == 1 and current_month == 1:
            rent_amount = yearly_rent
            should_send = True

        if should_send:
            send_rent_email(contract, round(rent_amount, 2))

def send_rent_email(contract, rent_amount):
    subject = f"Rent Payment Reminder - {contract.project_name}"
    message = f"""
    <p>Dear {contract.onwer_name},</p>
    <p>This is a reminder that your rent payment is due as per your rental contract:</p>
    <ul>
        <li><b>Contract:</b> {contract.name}</li>
        <li><b>Contract Type:</b> {contract.contract_type}</li>
        <li><b>Contract No:</b> {contract.contract_no}</li>
        <li><b>Start Date:</b> {contract.start_of_contract}</li>
        <li><b>End Date:</b> {contract.end_of_contract}</li>
        <li><b>Project:</b> {contract.project_name}</li>
        <li><b>Location:</b> {contract.location}</li>
        <li><b>Accommodation Type:</b> {contract.accommodation_type or "N/A"}</li>
        <li><b>Payment Frequency:</b> {contract.payment_frequency}</li>
        <li><b>Yearly Rent:</b> {contract.yearly_rent}</li>
    </ul>
    <p>Please ensure timely payment. Thank you.</p>
    <p>Regards,<br>Your Team</p>
    """

    attachment_file_names = get_attachments("Rental Contract",contract.name)

    frappe.sendmail(
        recipients=get_users_with_role("Accounts Manager"),
        subject=subject,
        message=message,
        reference_doctype="Rental Contract",
        reference_name=contract.name,
        attachments=attachment_file_names
    )
