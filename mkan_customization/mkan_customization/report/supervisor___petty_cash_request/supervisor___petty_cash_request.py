import frappe
from datetime import datetime, timedelta, date
import calendar
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}
    
    supervisor = filters.get("supervisor")
    duration = filters.get("duration") or "Daily"
    
    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee"},
        {"label": "Supervisor", "fieldname": "supervisor", "fieldtype": "Link", "options": "User"},
        {"label": "Petty Cash Request", "fieldname": "request", "fieldtype": "Link", "options": "Petty Cash Request"},
        {"label": "Request Date", "fieldname": "request_date", "fieldtype": "Date"},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency"},
        {"label": "Cost Center", "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center"},
        {"label":"Status","fieldname":"status","fieldtype":"data"},
        {"label":"Workflow Status","fieldname":"workflow_state","fieldtype":"data"},
        {"label":"Project","fieldname":"project","fieldtype":"link","options":"Project"},
        {"label":"Project Name","fieldname":"project_name","fieldtype":"data"},
        {"label":"Priority","fieldname":"priority","fieldtype":"data"},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department"},
    ]
    
    conditions = []
    values = []
    
    if supervisor:
        conditions.append("e.supervisor = %s")
        values.append(supervisor)
    
    # Get date range based on duration
    start_date, end_date = get_date_range(duration)
    
    if start_date and end_date:
        conditions.append("DATE(pc.creation) BETWEEN %s AND %s")
        values.extend([start_date, end_date])
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # SQL query to fetch data
    query = f"""
        SELECT 
            e.employee, 
            e.supervisor, 
            pc.name AS request,
            DATE(pc.creation) AS request_date,
            pc.required_amount AS amount,
            pc.cost_center,
            pc.status,
            pc.workflow_state,
            pc.project,
            p.project_name,
            pc.priority,
            pc.department
        FROM `tabPetty Cash Authorized Employees` e
        JOIN `tabPetty Cash Request` pc ON e.name = pc.employee
        JOIN `tabProject` p ON pc.project = p.name
        {where_clause}
        ORDER BY pc.creation
    """
    
    data = frappe.db.sql(query, tuple(values), as_dict=True)
    
    # Prepare chart data
    chart = prepare_continuous_bar_chart(data, duration, start_date, end_date)
    
    return columns, data, None, chart

def get_date_range(duration):
    today = datetime.now().date()
    
    if duration == "Daily":
        return today, today
    elif duration == "Weekly":
        return today - timedelta(days=6), today
    elif duration == "Monthly":
        start_date = (today.replace(day=1) - timedelta(days=365)).replace(day=1)
        return start_date, today
    elif duration == "Quarterly":
        start_date = today.replace(year=today.year-2, month=1, day=1)
        return start_date, today
    elif duration == "Yearly":
        start_date = today.replace(year=today.year-5, month=1, day=1)
        return start_date, today
    
    return None, None

def prepare_continuous_bar_chart(data, duration, start_date, end_date):
    if not data:
        data = []
    
    chart_data = {
        "data": {
            "labels": [],
            "datasets": [
                {
                    "name": "Petty Cash Requests",
                    "values": []
                }
            ]
        },
        "type": "bar",  # Changed to bar graph
        "colors": ["#7CD6FD"],  
        "axisOptions": {
            "xAxisMode": "tick",
            "yAxisMode": "tick",
            "xIsSeries": 1
        },
        "title": "Petty Cash Requests"
    }
    
    # Group data by date
    date_counts = {}
    
    for row in data:
        if not row.request_date:
            continue
            
        date_key = get_date_key(row.request_date, duration)
        
        if date_key not in date_counts:
            date_counts[date_key] = 0
        
        date_counts[date_key] += 1
    
    # Generate complete date series from start_date to end_date
    all_dates = generate_complete_date_series(start_date, end_date, duration)
    
    # Fill in zeros for missing dates to ensure continuous bar chart
    for date_key in all_dates:
        if date_key not in date_counts:
            date_counts[date_key] = 0
    
    # Sort keys chronologically
    sorted_keys = sorted(date_counts.keys(), key=lambda x: get_sort_key(x, duration))
    
    # Populate chart data
    for key in sorted_keys:
        chart_data["data"]["labels"].append(key)
        chart_data["data"]["datasets"][0]["values"].append(date_counts[key])
    
    return chart_data

def generate_complete_date_series(start_date, end_date, duration):
    """Generate a complete series of dates from start_date to end_date"""
    if not start_date or not end_date:
        return []
    
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    date_series = []
    
    if duration == "Daily":
        current_date = start_date
        while current_date <= end_date:
            date_series.append(get_date_key(current_date, duration))
            current_date += timedelta(days=1)
    
    elif duration == "Weekly":
        start_week = start_date - timedelta(days=start_date.weekday())
        current_date = start_week
        while current_date <= end_date:
            date_series.append(get_date_key(current_date, duration))
            current_date += timedelta(days=7)
    
    elif duration == "Monthly":
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            date_series.append(get_date_key(current_date, duration))
            
            # Move to next month
            month = current_date.month + 1
            year = current_date.year
            if month > 12:
                month = 1
                year += 1
            
            last_day = calendar.monthrange(year, month)[1]
            next_month = date(year, month, min(current_date.day, last_day))
            current_date = next_month.replace(day=1)
    
    elif duration == "Quarterly":
        current_date = date(start_date.year, ((start_date.month - 1) // 3) * 3 + 1, 1)
        while current_date <= end_date:
            date_series.append(get_date_key(current_date, duration))
            
            month = current_date.month + 3
            year = current_date.year
            if month > 12:
                month = month - 12
                year += 1
            
            current_date = date(year, month, 1)
    
    elif duration == "Yearly":
        for year in range(start_date.year, end_date.year + 1):
            date_series.append(str(year))
    
    return date_series

def get_date_key(date_str, duration):
    if isinstance(date_str, str):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        date_obj = date_str
    
    if duration == "Daily":
        return date_obj.strftime("%d-%m-%Y")
    elif duration == "Weekly":
        week_start = date_obj - timedelta(days=date_obj.weekday())
        return week_start.strftime("%d-%m-%Y")
    elif duration == "Monthly":
        return date_obj.strftime("%b %Y")
    elif duration == "Quarterly":
        quarter = (date_obj.month - 1) // 3 + 1
        return f"Q{quarter} {date_obj.year}"
    elif duration == "Yearly":
        return str(date_obj.year)
    
    return date_obj.strftime("%d-%m-%Y")

def get_sort_key(date_key, duration):
    """Generate a sortable key for the date string"""
    if duration == "Daily":
        return datetime.strptime(date_key, "%d-%m-%Y")
    elif duration == "Weekly":
        return datetime.strptime(date_key, "%d-%m-%Y")
    elif duration == "Monthly":
        return datetime.strptime(date_key, "%b %Y")
    elif duration == "Quarterly":
        quarter = int(date_key[1])
        year = int(date_key.split(" ")[1])
        month = (quarter - 1) * 3 + 1
        return datetime(year, month, 1) 
    elif duration == "Yearly":
        return datetime(int(date_key), 1, 1)
    
    return date_key

@frappe.whitelist()
def get_petty_cash_requests():
    supervisor = frappe.session.user  # Ensure it always uses the logged-in user
    
    if not supervisor:
        frappe.throw(_("Supervisor is required"))
    
    # Fetch all authorized user_ids for the supervisor
    user_ids = frappe.get_all(
        "Petty Cash Authorized Employees", 
        filters={"supervisor": supervisor}, 
        pluck="user_id"
    )
    
    return user_ids if user_ids else []
