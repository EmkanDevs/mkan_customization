import frappe
from datetime import datetime, timedelta, date
import calendar

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
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency"}
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
            pc.required_amount AS amount
        FROM `tabPetty Cash Authorized Employees` e
        JOIN `tabPetty Cash Request` pc ON e.name = pc.employee
        {where_clause}
        ORDER BY pc.creation
    """
    
    data = frappe.db.sql(query, tuple(values), as_dict=True)
    
    # Prepare chart data
    chart = prepare_continuous_line_chart(data, duration, start_date, end_date)
    
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

def prepare_continuous_line_chart(data, duration, start_date, end_date):
    if not data:
        # If no data, still create a chart with the full date range
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
        "type": "line",
        "colors": ["#7CD6FD"],  
        "lineOptions": {
            "regionFill": 1,     
            "hideDots": 0,       # Show dots at data points
            "spline": 1,         # Use curved lines
            "heatline": 0        # No heatline coloring
        },
        "axisOptions": {
            "xAxisMode": "tick",
            "yAxisMode": "tick",
            "xIsSeries": 1
        },
        # Removed the JavaScript arrow function syntax
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
    
    # Fill in zeros for missing dates to ensure continuous line
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
        # Start from the beginning of the week containing start_date
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
            
            # Handle month transitions
            last_day = calendar.monthrange(year, month)[1]
            next_month = date(year, month, min(current_date.day, last_day))
            current_date = next_month.replace(day=1)
    
    elif duration == "Quarterly":
        current_date = date(start_date.year, ((start_date.month - 1) // 3) * 3 + 1, 1)
        while current_date <= end_date:
            date_series.append(get_date_key(current_date, duration))
            
            # Move to next quarter
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
        return date_obj.strftime("%d-%m-%Y")  # DD-MM-YYYY format
    elif duration == "Weekly":
        # Use the first day of the week as the key
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
        # Format depends on the get_date_key format
        return datetime.strptime(date_key, "%d-%m-%Y")
    elif duration == "Monthly":
        return datetime.strptime(date_key, "%b %Y")
    elif duration == "Quarterly":
        # Format: "QX YYYY"
        quarter = int(date_key[1])
        year = int(date_key.split(" ")[1])
        month = (quarter - 1) * 3 + 1
        return datetime(year, month, 1) 
    elif duration == "Yearly":
        return datetime(int(date_key), 1, 1)
    
    return date_key