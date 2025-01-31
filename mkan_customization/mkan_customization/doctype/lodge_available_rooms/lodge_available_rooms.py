# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import random
import string
from datetime import datetime
import frappe
from frappe import _


class LodgeAvailableRooms(Document):
	def before_insert(self):
		self.random_reservation_id()
	
	def on_update_after_submit(self):
		self.set_values()
	
	def random_reservation_id(self): 
		N = 12
		res = ''.join(random.choices(string.digits, k=N))
		self.reservation_id = res
	def validate(self):
		self.set_values()
		if self.lodge and self.available_capacity == 0:
			frappe.throw("Please prefer another lodge")
		if self.total_number_of_occupants > self.available_capacity:
			frappe.throw(_("Current Capacity is this lodge is {0}").format(self.available_capacity))
	def set_values(self):
		count = 0 
		for row in self.details:
			if row.check_in_date and row.check_out_date:
				start_date = datetime.strptime(row.check_in_date, "%Y-%m-%d")
				end_date = datetime.strptime(row.check_out_date, "%Y-%m-%d")
			
				date_diff = (end_date - start_date).days
				row.db_set("duration_of_stay" , date_diff)
			else:
				row.duration_of_stay = 0
			if row.number_of_occupants:
				count += row.number_of_occupants

		self.total_number_of_occupants =  count
	
	
	def on_submit(self):
		if self.total_number_of_occupants and self.lodge:
			available_capacity = self.available_capacity
			current_capacity = self.current_capacity
			if available_capacity >= self.total_number_of_occupants:
				frappe.db.set_value(
					"Lodge", 
					self.lodge, 
					"current_capacity", 
					current_capacity + self.total_number_of_occupants
				)
				frappe.db.set_value(
					"Lodge", 
					self.lodge, 
					"available_capacity", 
					available_capacity - self.total_number_of_occupants
				)
			else:
				frappe.throw(
					_("The lodge does not have enough capacity for {0} occupants. Only {1} are available.").format(
						self.total_number_of_occupants, current_capacity
					)
				)
	def on_cancel(self):
		if self.total_number_of_occupants and self.lodge:
			current_capacity = frappe.db.get_value("Lodge",self.lodge,"current_capacity")
			available_capacity = frappe.db.get_value("Lodge",self.lodge,"available_capacity")
			frappe.db.set_value(
				"Lodge", 
				self.lodge, 
				"current_capacity", 
				current_capacity - self.total_number_of_occupants
			)
			frappe.db.set_value(
				"Lodge", 
				self.lodge, 
				"available_capacity", 
				available_capacity + self.total_number_of_occupants
			)



def update_room_capacities():
	from datetime import datetime
	today = datetime.today().date()
	
	parents = frappe.get_all(
		"Lodge Available Rooms",  
		fields=["name"],
		filters={"docstatus": 1}
	)
	
	for parent in parents:
		doc = frappe.get_doc("Lodge Available Rooms", parent.name)
		
		for room in doc.get("details"):
			if room.check_out_date and room.check_out_date <= today:
				lodge_doc = frappe.get_doc("Lodge", doc.lodge)
				new_capacity = lodge_doc.current_capacity - room.number_of_occupants
				new_available = lodge_doc.available_capacity + room.number_of_occupants
				lodge_doc.db_set("current_capacity", new_capacity)
				lodge_doc.db_set("available_capacity", new_available)
	
	frappe.db.commit()
