import frappe
import random
# from frappe.model.naming import make_autoname

def before_insert(doc, method):
    
    if not doc.custom_car_number:
        # Generate a random 5-digit number
        random_number = random.randint(10000, 99999)

        # Ensure uniqueness by checking for existing CAR numbers
        while frappe.db.exists("Quality Action", {"custom_car_number": str(random_number)}):
            random_number = random.randint(10000, 99999)

        doc.custom_car_number = str(random_number)
        
