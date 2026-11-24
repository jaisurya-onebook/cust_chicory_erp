import frappe
from frappe import _
from cust_chicory_erp.setup.custom_fields import setup_custom_fields


def setup_chicory_masters(company=None):
	"""
	Idempotent master data setup for Chicory Powder Manufacturing ERP.
	Configures Company, Warehouses, Item Groups, Items, Workstations,
	Operations, Routing, BOM, Suppliers, and Customers.
	"""
	# Ensure custom fields exist first
	setup_custom_fields()

	# 1. Company
	if not company:
		company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		companies = frappe.get_all("Company", pluck="name")
		company = companies[0] if companies else "chicory"

	if not frappe.db.exists("Company", company):
		company_doc = frappe.get_doc({
			"doctype": "Company",
			"company_name": company,
			"abbr": "Cc",
			"default_currency": "INR",
			"country": "India",
		})
		company_doc.insert(ignore_permissions=True)
	else:
		company_doc = frappe.get_doc("Company", company)

	abbr = company_doc.abbr
	frappe.db.set_single_value("Global Defaults", "default_company", company)
	exp_val_acc = f"Expenses Included In Valuation - {abbr}"
	if frappe.db.exists("Account", exp_val_acc) and company_doc.default_operating_cost_account != exp_val_acc:
		frappe.db.set_value("Company", company, "default_operating_cost_account", exp_val_acc)

	# 2. Warehouses
	# Parent warehouse
	parent_wh = f"All Warehouses - {abbr}"
	if not frappe.db.exists("Warehouse", parent_wh):
		parent_doc = frappe.get_doc({
			"doctype": "Warehouse",
			"warehouse_name": "All Warehouses",
			"company": company,
			"is_group": 1,
		})
		parent_doc.insert(ignore_permissions=True)

	warehouses_to_create = [
		"Raw Material",
		"Quality Hold",
		"WIP Production",
		"Finished Goods",
		"Packaging Stores",
		"Reject / Scrap",
	]

	created_warehouses = {}
	for wh_name in warehouses_to_create:
		wh_id = f"{wh_name} - {abbr}"
		if not frappe.db.exists("Warehouse", wh_id):
			wh = frappe.get_doc({
				"doctype": "Warehouse",
				"warehouse_name": wh_name,
				"company": company,
				"parent_warehouse": parent_wh,
				"is_group": 0,
			})
			wh.insert(ignore_permissions=True)
			created_warehouses[wh_name] = wh.name
		else:
			created_warehouses[wh_name] = wh_id

	# 3. Item Groups
	item_groups = [
		"Chicory Raw Material",
		"Chicory Semi-Finished",
		"Chicory Finished Goods",
		"Chicory Packaging",
	]

	for ig_name in item_groups:
		if not frappe.db.exists("Item Group", ig_name):
			ig = frappe.get_doc({
				"doctype": "Item Group",
				"item_group_name": ig_name,
				"parent_item_group": "All Item Groups",
				"is_group": 0,
			})
			ig.insert(ignore_permissions=True)

	# 4. Items
	raw_wh = created_warehouses.get("Raw Material") or f"Raw Material - {abbr}"
	wip_wh = created_warehouses.get("WIP Production") or f"WIP Production - {abbr}"
	fg_wh = created_warehouses.get("Finished Goods") or f"Finished Goods - {abbr}"
	pkg_wh = created_warehouses.get("Packaging Stores") or f"Packaging Stores - {abbr}"

	items_def = [
		{
			"item_code": "RAW-CHICORY-ROOT",
			"item_name": "Raw Chicory Root",
			"item_group": "Chicory Raw Material",
			"stock_uom": "Kg",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "ROOT-.YYYY.-.#####",
			"inspection_required_before_purchase": 1,
			"valuation_method": "FIFO",
			"default_warehouse": raw_wh,
		},
		{
			"item_code": "DRIED-CHICORY",
			"item_name": "Dried Chicory",
			"item_group": "Chicory Semi-Finished",
			"stock_uom": "Kg",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "DRY-.YYYY.-.#####",
			"valuation_method": "FIFO",
			"default_warehouse": wip_wh,
		},
		{
			"item_code": "ROASTED-CHICORY",
			"item_name": "Roasted Chicory",
			"item_group": "Chicory Semi-Finished",
			"stock_uom": "Kg",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "RST-.YYYY.-.#####",
			"valuation_method": "FIFO",
			"default_warehouse": wip_wh,
		},
		{
			"item_code": "BULK-CHICORY-POWDER",
			"item_name": "Bulk Chicory Powder",
			"item_group": "Chicory Semi-Finished",
			"stock_uom": "Kg",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "BLK-.YYYY.-.#####",
			"valuation_method": "FIFO",
			"default_warehouse": wip_wh,
		},
		{
			"item_code": "POUCH-1KG",
			"item_name": "Pouch 1Kg",
			"item_group": "Chicory Packaging",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"has_batch_no": 0,
			"valuation_method": "Moving Average",
			"default_warehouse": pkg_wh,
		},
		{
			"item_code": "CHICORY-POWDER-1KG",
			"item_name": "Chicory Powder 1Kg",
			"item_group": "Chicory Finished Goods",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"has_batch_no": 1,
			"create_new_batch": 1,
			"batch_number_series": "CP1K-.YYYY.-.#####",
			"has_expiry_date": 1,
			"shelf_life_in_days": 365,
			"valuation_method": "FIFO",
			"default_warehouse": fg_wh,
		},
	]

	for item_data in items_def:
		code = item_data["item_code"]
		if frappe.db.exists("Item", code):
			item = frappe.get_doc("Item", code)
			for key, val in item_data.items():
				setattr(item, key, val)
			item.save(ignore_permissions=True)
		else:
			item = frappe.get_doc({"doctype": "Item", **item_data})
			item.insert(ignore_permissions=True)

	# 5. Workstations
	workstations = [
		{"workstation_name": "Root Washer", "hour_rate": 100.0},
		{"workstation_name": "Slicer Unit", "hour_rate": 120.0},
		{"workstation_name": "Drying Yard", "hour_rate": 80.0},
		{"workstation_name": "Rotary Roaster", "hour_rate": 150.0},
		{"workstation_name": "Pulverizer Mill", "hour_rate": 180.0},
		{"workstation_name": "Automatic Bagging Line", "hour_rate": 160.0},
	]

	for ws_data in workstations:
		name = ws_data["workstation_name"]
		if not frappe.db.exists("Workstation", name):
			ws = frappe.get_doc({"doctype": "Workstation", **ws_data})
			ws.insert(ignore_permissions=True)

	# 6. Operations
	operations = [
		{"operation": "Washing", "workstation": "Root Washer"},
		{"operation": "Slicing", "workstation": "Slicer Unit"},
		{"operation": "Drying", "workstation": "Drying Yard"},
		{"operation": "Roasting", "workstation": "Rotary Roaster"},
		{"operation": "Grinding & Sieving", "workstation": "Pulverizer Mill"},
		{"operation": "Packing", "workstation": "Automatic Bagging Line"},
	]

	for op_data in operations:
		op_name = op_data["operation"]
		if frappe.db.exists("Operation", op_name):
			op = frappe.get_doc("Operation", op_name)
			op.workstation = op_data["workstation"]
			op.save(ignore_permissions=True)
		else:
			op = frappe.get_doc({
				"doctype": "Operation",
				"name": op_name,
				"workstation": op_data["workstation"],
			})
			op.insert(ignore_permissions=True)

	# 7. Routing
	routing_name = "Chicory Powder Multi-Operation Routing"
	routing_ops = [
		{"operation": "Washing", "workstation": "Root Washer", "time_in_mins": 30.0, "sequence_id": 1},
		{"operation": "Slicing", "workstation": "Slicer Unit", "time_in_mins": 30.0, "sequence_id": 2},
		{"operation": "Drying", "workstation": "Drying Yard", "time_in_mins": 30.0, "sequence_id": 3},
		{"operation": "Roasting", "workstation": "Rotary Roaster", "time_in_mins": 30.0, "sequence_id": 4},
		{"operation": "Grinding & Sieving", "workstation": "Pulverizer Mill", "time_in_mins": 30.0, "sequence_id": 5},
		{"operation": "Packing", "workstation": "Automatic Bagging Line", "time_in_mins": 30.0, "sequence_id": 6},
	]

	if not frappe.db.exists("Routing", routing_name):
		routing = frappe.get_doc({
			"doctype": "Routing",
			"routing_name": routing_name,
			"operations": routing_ops,
		})
		routing.insert(ignore_permissions=True)
	else:
		routing = frappe.get_doc("Routing", routing_name)
		routing.set("operations", routing_ops)
		routing.save(ignore_permissions=True)

	# 8. BOM (Multi-operation BOM)
	# Output: CHICORY-POWDER-1KG (Qty: 100 Nos)
	# Raw materials: RAW-CHICORY-ROOT (200 Kg), POUCH-1KG (100 Nos)
	bom_items = [
		{
			"item_code": "RAW-CHICORY-ROOT",
			"qty": 200.0,
			"uom": "Kg",
			"stock_uom": "Kg",
			"rate": 20.0,
		},
		{
			"item_code": "POUCH-1KG",
			"qty": 100.0,
			"uom": "Nos",
			"stock_uom": "Nos",
			"rate": 3.0,
		},
	]

	# Check existing BOM for CHICORY-POWDER-1KG
	existing_bom_name = frappe.db.get_value(
		"BOM",
		{
			"item": "CHICORY-POWDER-1KG",
			"is_active": 1,
			"is_default": 1,
			"docstatus": 1,
			"routing": routing_name,
		},
	)

	if not existing_bom_name:
		# Uncheck is_default on old BOMs for this item
		for old_bom in frappe.get_all("BOM", filters={"item": "CHICORY-POWDER-1KG"}):
			frappe.db.set_value("BOM", old_bom.name, "is_default", 0)

		bom = frappe.get_doc({
			"doctype": "BOM",
			"item": "CHICORY-POWDER-1KG",
			"quantity": 100.0,
			"company": company,
			"currency": company_doc.default_currency or "INR",
			"is_active": 1,
			"is_default": 1,
			"with_operations": 1,
			"routing": routing_name,
			"items": bom_items,
			"operations": [
				{
					"operation": "Washing",
					"workstation": "Root Washer",
					"time_in_mins": 30.0,
					"sequence_id": 1,
					"hour_rate": 100.0,
				},
				{
					"operation": "Slicing",
					"workstation": "Slicer Unit",
					"time_in_mins": 30.0,
					"sequence_id": 2,
					"hour_rate": 120.0,
				},
				{
					"operation": "Drying",
					"workstation": "Drying Yard",
					"time_in_mins": 30.0,
					"sequence_id": 3,
					"hour_rate": 80.0,
				},
				{
					"operation": "Roasting",
					"workstation": "Rotary Roaster",
					"time_in_mins": 30.0,
					"sequence_id": 4,
					"hour_rate": 150.0,
				},
				{
					"operation": "Grinding & Sieving",
					"workstation": "Pulverizer Mill",
					"time_in_mins": 30.0,
					"sequence_id": 5,
					"hour_rate": 180.0,
				},
				{
					"operation": "Packing",
					"workstation": "Automatic Bagging Line",
					"time_in_mins": 30.0,
					"sequence_id": 6,
					"hour_rate": 160.0,
				},
			],
		})
		bom.insert(ignore_permissions=True)
		bom.submit()

	# 9. Suppliers & Customers
	# Supplier: Chicory Farmer Cooperative
	supp1_group = "Raw Material" if frappe.db.exists("Supplier Group", "Raw Material") else "All Supplier Groups"
	if not frappe.db.exists("Supplier", {"supplier_name": "Chicory Farmer Cooperative"}):
		supp1 = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": "Chicory Farmer Cooperative",
			"supplier_group": supp1_group,
			"supplier_type": "Company",
			"country": "India",
		})
		supp1.insert(ignore_permissions=True)

	# Supplier: Chicory Express Logistics
	serv_group = "Services" if frappe.db.exists("Supplier Group", "Services") else "All Supplier Groups"
	supp2_name = frappe.db.get_value("Supplier", {"supplier_name": "Chicory Express Logistics"})
	if not supp2_name:
		supp2 = frappe.get_doc({
			"doctype": "Supplier",
			"supplier_name": "Chicory Express Logistics",
			"supplier_group": serv_group,
			"is_transporter": 1,
			"supplier_type": "Company",
			"country": "India",
		})
		supp2.insert(ignore_permissions=True)
	else:
		supp2 = frappe.get_doc("Supplier", supp2_name)
		supp2.is_transporter = 1
		supp2.save(ignore_permissions=True)

	# Customer: National Coffee & Beverage Co.
	cust_group = "Commercial" if frappe.db.exists("Customer Group", "Commercial") else "All Customer Groups"
	territory = "India" if frappe.db.exists("Territory", "India") else "All Territories"
	if not frappe.db.exists("Customer", {"customer_name": "National Coffee & Beverage Co."}):
		cust = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "National Coffee & Beverage Co.",
			"customer_group": cust_group,
			"territory": territory,
			"customer_type": "Company",
		})
		cust.insert(ignore_permissions=True)

	setup_chicory_workers(company)
	setup_chicory_dock()
	setup_chicory_dashboard_and_components()
	setup_chicory_sidebar()
	setup_chicory_desktop_icon()

	if not frappe.flags.in_test:
		print(_("Chicory masters setup completed successfully for company: {0}").format(company))
	return True


def setup_chicory_workers(company=None):
	"""Ensure standard factory worker profiles and designations exist for shop-floor tracking."""
	if not company:
		company = frappe.db.get_single_value("Global Defaults", "default_company") or "Chicory Agro Industries Ltd"

	workers = [
		{"first_name": "Anil Sharma", "designation": "Weighbridge Operator"},
		{"first_name": "Mahesh Yadav", "designation": "Washing & Drying Operator"},
		{"first_name": "Ramesh Kumar", "designation": "Roaster Operator"},
		{"first_name": "Suresh Patel", "designation": "Grinder Operator"},
		{"first_name": "Dinesh Kumar", "designation": "Packing Line Operator"},
		{"first_name": "Pooja Verma", "designation": "Quality Control Chemist"},
	]

	for w in workers:
		if not frappe.db.exists("Designation", w["designation"]):
			d = frappe.get_doc({
				"doctype": "Designation",
				"designation_name": w["designation"],
			})
			d.insert(ignore_permissions=True)

		if not frappe.db.exists("Employee", {"first_name": w["first_name"], "company": company}):
			emp = frappe.get_doc({
				"doctype": "Employee",
				"first_name": w["first_name"],
				"designation": w["designation"],
				"company": company,
				"gender": "Male" if "Verma" not in w["first_name"] else "Female",
				"date_of_birth": "1992-05-15",
				"date_of_joining": "2024-01-01",
				"status": "Active",
			})
			emp.insert(ignore_permissions=True)


def setup_chicory_dock():
	"""Ensure Dock document exists for cust_chicory_erp app in Frappe v16 Desk."""
	if not frappe.db.exists("DocType", "Dock"):
		return
	items = [
		{
			"link_type": "Sidebar",
			"link_to": "Cust Chicory Erp",
			"icon": "factory-soft",
			"title": "Chicory Manufacturing",
		}
	]
	if not frappe.db.exists("Dock", "cust_chicory_erp"):
		dock = frappe.get_doc({
			"doctype": "Dock",
			"name": "cust_chicory_erp",
			"app": "cust_chicory_erp",
			"standard": 1,
			"user": "",
			"items": items,
		})
		dock.flags.ignore_permissions = True
		dock.flags.ignore_mandatory = True
		dock.insert()
	else:
		dock = frappe.get_doc("Dock", "cust_chicory_erp")
		dock.items = []
		for it in items:
			dock.append("items", it)
		dock.save(ignore_permissions=True)
	frappe.cache.delete_key("dock_layers")


def setup_chicory_desktop_icon():
	"""Ensure Desktop Icon document exists for cust_chicory_erp app on /desk."""
	if not frappe.db.exists("DocType", "Desktop Icon"):
		return
	icon_name = "Chicory ERP"
	icon_data = {
		"doctype": "Desktop Icon",
		"name": icon_name,
		"label": icon_name,
		"app": "cust_chicory_erp",
		"icon_type": "App",
		"link_type": "External",
		"link": "/desk/cust-chicory-erp/dashboard-view/Chicory%20Manufacturing",
		"logo_url": "/assets/cust_chicory_erp/images/chicory-logo.svg",
		"hidden": 0,
		"idx": 3,
		"standard": 1,
	}
	if not frappe.db.exists("Desktop Icon", icon_name):
		doc = frappe.get_doc(icon_data)
		doc.flags.ignore_permissions = True
		doc.insert()
	else:
		frappe.db.set_value("Desktop Icon", icon_name, {
			"hidden": 0,
			"link": "/desk/cust-chicory-erp/dashboard-view/Chicory%20Manufacturing",
			"logo_url": "/assets/cust_chicory_erp/images/chicory-logo.svg",
		})
	frappe.clear_cache()


def setup_chicory_dashboard_and_components():
	"""Ensure standard Frappe Dashboard, Charts, and Number Cards exist."""
	import json

	# 1. Total Raw Roots Inward Card
	card_name = "Total Raw Roots Inward (Kg)"
	if not frappe.db.exists("Number Card", card_name):
		c = frappe.get_doc({
			"doctype": "Number Card",
			"name": card_name,
			"label": card_name,
			"function": "Sum",
			"document_type": "Chicory Root Inward",
			"aggregate_function_based_on": "net_weight",
			"is_standard": 1,
			"module": "Cust Chicory Erp",
			"color": "#6F3918",
			"filters_json": json.dumps([["Chicory Root Inward", "docstatus", "=", 1]]),
		})
		c.insert(ignore_permissions=True)
	else:
		frappe.db.set_value("Number Card", card_name, "aggregate_function_based_on", "net_weight")

	# 2. Total Finished Powder Produced Card
	card_mfg = "Total Finished Powder Produced"
	if not frappe.db.exists("Number Card", card_mfg):
		c2 = frappe.get_doc({
			"doctype": "Number Card",
			"name": card_mfg,
			"label": card_mfg,
			"function": "Sum",
			"document_type": "Work Order",
			"aggregate_function_based_on": "produced_qty",
			"is_standard": 1,
			"module": "Cust Chicory Erp",
			"color": "#2B8256",
			"filters_json": json.dumps([["Work Order", "docstatus", "=", 1]]),
		})
		c2.insert(ignore_permissions=True)

	# 3. Chart: Chicory Root Inward
	chart1_name = "Chicory Root Inward"
	if frappe.db.exists("Dashboard Chart", "Chicory Root Inward Trends"):
		frappe.delete_doc("Dashboard Chart", "Chicory Root Inward Trends", ignore_permissions=True, force=True)

	if not frappe.db.exists("Dashboard Chart", chart1_name):
		ch1 = frappe.get_doc({
			"doctype": "Dashboard Chart",
			"chart_name": chart1_name,
			"chart_type": "Sum",
			"document_type": "Chicory Root Inward",
			"based_on": "posting_date",
			"value_based_on": "net_weight",
			"type": "Bar",
			"timespan": "Last Year",
			"time_interval": "Monthly",
			"is_standard": 1,
			"module": "Cust Chicory Erp",
			"color": "#6F3918",
			"filters_json": json.dumps([["Chicory Root Inward", "docstatus", "=", 1]]),
		})
		ch1.insert(ignore_permissions=True)
	else:
		frappe.db.set_value("Dashboard Chart", chart1_name, {
			"based_on": "posting_date",
			"value_based_on": "net_weight",
		})

	# 4. Chart: Chicory Powder Production Output
	chart2_name = "Chicory Powder Production Output"
	if not frappe.db.exists("Dashboard Chart", chart2_name):
		ch2 = frappe.get_doc({
			"doctype": "Dashboard Chart",
			"chart_name": chart2_name,
			"chart_type": "Sum",
			"document_type": "Work Order",
			"based_on": "creation",
			"value_based_on": "produced_qty",
			"type": "Line",
			"timespan": "Last Year",
			"time_interval": "Monthly",
			"is_standard": 1,
			"module": "Cust Chicory Erp",
			"color": "#2B8256",
			"filters_json": json.dumps([["Work Order", "docstatus", "=", 1]]),
		})
		ch2.insert(ignore_permissions=True)

	# 5. Chart: Finished Goods Dispatches
	chart3_name = "Chicory Powder Dispatches"
	if not frappe.db.exists("Dashboard Chart", chart3_name):
		ch3 = frappe.get_doc({
			"doctype": "Dashboard Chart",
			"chart_name": chart3_name,
			"chart_type": "Sum",
			"document_type": "Delivery Note",
			"based_on": "posting_date",
			"value_based_on": "total_qty",
			"type": "Bar",
			"timespan": "Last Year",
			"time_interval": "Monthly",
			"is_standard": 1,
			"module": "Cust Chicory Erp",
			"color": "#1F77B4",
			"filters_json": json.dumps([["Delivery Note", "docstatus", "=", 1]]),
		})
		ch3.insert(ignore_permissions=True)

	# 6. Chart: Quality Inspection Verdicts
	chart4_name = "Quality Inspection Verdicts"
	if not frappe.db.exists("Dashboard Chart", chart4_name):
		ch4 = frappe.get_doc({
			"doctype": "Dashboard Chart",
			"chart_name": chart4_name,
			"chart_type": "Group By",
			"document_type": "Quality Inspection",
			"group_by_based_on": "status",
			"aggregate_function_based_on": "name",
			"type": "Donut",
			"is_standard": 1,
			"module": "Cust Chicory Erp",
			"color": "#FF8C00",
			"filters_json": json.dumps([["Quality Inspection", "docstatus", "=", 1]]),
		})
		ch4.insert(ignore_permissions=True)

	# 7. Dashboard Document
	dash_name = "Chicory Manufacturing"
	if not frappe.db.exists("Dashboard", dash_name):
		d = frappe.get_doc({
			"doctype": "Dashboard",
			"name": dash_name,
			"dashboard_name": dash_name,
			"module": "Cust Chicory Erp",
			"is_default": 1,
			"is_standard": 1,
			"cards": [
				{"card": "Total Raw Roots Inward (Kg)"},
				{"card": "Total Finished Powder Produced"},
				{"card": "Raw Root Stock (Kg)"},
				{"card": "Finished Powder Available (Nos)"},
				{"card": "Active Work Orders"},
				{"card": "Roots on Quality Hold (Kg)"},
			],
			"charts": [
				{"chart": "Chicory Root Inward", "width": "Half"},
				{"chart": "Chicory Powder Production Output", "width": "Half"},
				{"chart": "Chicory Powder Dispatches", "width": "Half"},
				{"chart": "Quality Inspection Verdicts", "width": "Half"},
			],
		})
		d.insert(ignore_permissions=True)
	else:
		dash = frappe.get_doc("Dashboard", dash_name)
		dash.charts = []
		for ch in [
			{"chart": "Chicory Root Inward", "width": "Half"},
			{"chart": "Chicory Powder Production Output", "width": "Half"},
			{"chart": "Chicory Powder Dispatches", "width": "Half"},
			{"chart": "Quality Inspection Verdicts", "width": "Half"},
		]:
			dash.append("charts", ch)
		dash.save(ignore_permissions=True)

	# 8. Workspace Content Update
	if frappe.db.exists("Workspace", "Chicory Food Manufacturing"):
		ws = frappe.get_doc("Workspace", "Chicory Food Manufacturing")
		ws.charts = []
		for c_name in [
			"Chicory Root Inward",
			"Chicory Powder Production Output",
			"Chicory Powder Dispatches",
			"Quality Inspection Verdicts",
		]:
			ws.append("charts", {"chart_name": c_name, "label": c_name})

		content = [
			{"id": "hdr_kpi", "type": "header", "data": {"text": "Chicory Manufacturing Live KPIs", "level": 4, "col": 12}},
			{"id": "nc_inward", "type": "number_card", "data": {"number_card_name": "Total Raw Roots Inward (Kg)", "col": 4}},
			{"id": "nc_mfg", "type": "number_card", "data": {"number_card_name": "Total Finished Powder Produced", "col": 4}},
			{"id": "nc_active", "type": "number_card", "data": {"number_card_name": "Active Work Orders", "col": 4}},
			{"id": "nc_stock_root", "type": "number_card", "data": {"number_card_name": "Raw Root Stock (Kg)", "col": 4}},
			{"id": "nc_stock_fg", "type": "number_card", "data": {"number_card_name": "Finished Powder Available (Nos)", "col": 4}},
			{"id": "nc_hold", "type": "number_card", "data": {"number_card_name": "Roots on Quality Hold (Kg)", "col": 4}},

			{"id": "hdr_charts", "type": "header", "data": {"text": "Production & Quality Analytics Dashboard", "level": 4, "col": 12}},
			{"id": "ch_inward", "type": "chart", "data": {"chart_name": "Chicory Root Inward", "col": 6}},
			{"id": "ch_mfg", "type": "chart", "data": {"chart_name": "Chicory Powder Production Output", "col": 6}},
			{"id": "ch_sales", "type": "chart", "data": {"chart_name": "Chicory Powder Dispatches", "col": 6}},
			{"id": "ch_qa", "type": "chart", "data": {"chart_name": "Quality Inspection Verdicts", "col": 6}},

			{"id": "hdr_sc", "type": "header", "data": {"text": "Quick Operations (13 Stages)", "level": 4, "col": 12}},
			{"id": "sc_0", "type": "shortcut", "data": {"shortcut_name": "New Root Inward Slip", "col": 3}},
			{"id": "sc_1", "type": "shortcut", "data": {"shortcut_name": "Create Purchase Receipt", "col": 3}},
			{"id": "sc_2", "type": "shortcut", "data": {"shortcut_name": "Landed Cost Voucher", "col": 3}},
			{"id": "sc_3", "type": "shortcut", "data": {"shortcut_name": "New Quality Inspection", "col": 3}},
			{"id": "sc_4", "type": "shortcut", "data": {"shortcut_name": "New Work Order", "col": 3}},
			{"id": "sc_5", "type": "shortcut", "data": {"shortcut_name": "Material Transfer", "col": 3}},
			{"id": "sc_6", "type": "shortcut", "data": {"shortcut_name": "Open Job Cards", "col": 3}},
			{"id": "sc_7", "type": "shortcut", "data": {"shortcut_name": "Manufacture Entry", "col": 3}},
			{"id": "sc_8", "type": "shortcut", "data": {"shortcut_name": "Batch Traceability", "col": 3}},

			{"id": "hdr_links", "type": "header", "data": {"text": "Workflow Process Links & Master Documents", "level": 4, "col": 12}},
			{"id": "card_0", "type": "card", "data": {"card_name": "Inward & Quality", "col": 6}},
			{"id": "card_1", "type": "card", "data": {"card_name": "Stock & Landed Costs", "col": 6}},
			{"id": "card_2", "type": "card", "data": {"card_name": "Production & Job Cards", "col": 6}},
			{"id": "card_3", "type": "card", "data": {"card_name": "Sales & Traceability", "col": 6}},
		]
		ws.content = json.dumps(content)
		ws.save(ignore_permissions=True)


def setup_chicory_sidebar():
	"""Ensure clean, icon-rich Sidebar matching Frappe v16 style exists for Cust Chicory Erp."""
	if not frappe.db.exists("DocType", "Sidebar"):
		return

	items_data = [
		# Top-level navigation (Overall Dashboard)
		{"type": "Link", "label": "Overall Dashboard", "link_type": "Dashboard", "link_to": "Chicory Manufacturing", "icon": "layout-grid", "child": 0, "indent": 0, "collapsible": 1},

		# Section 1: Procurement
		{"type": "Section Break", "label": "Procurement", "link_type": "DocType", "link_to": None, "icon": "shopping-cart", "child": 0, "indent": 1, "collapsible": 1},
		{"type": "Link", "label": "Chicory Root Inward", "link_type": "DocType", "link_to": "Chicory Root Inward", "icon": "scale", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Purchase Order", "link_type": "DocType", "link_to": "Purchase Order", "icon": "shopping-cart", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Purchase Receipt", "link_type": "DocType", "link_to": "Purchase Receipt", "icon": "package-check", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Supplier", "link_type": "DocType", "link_to": "Supplier", "icon": "truck", "child": 1, "indent": 0, "collapsible": 1},

		# Section 2: Quality
		{"type": "Section Break", "label": "Quality", "link_type": "DocType", "link_to": None, "icon": "shield-check", "child": 0, "indent": 1, "collapsible": 1},
		{"type": "Link", "label": "Quality Inspection", "link_type": "DocType", "link_to": "Quality Inspection", "icon": "clipboard-check", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Batch", "link_type": "DocType", "link_to": "Batch", "icon": "layers", "child": 1, "indent": 0, "collapsible": 1},

		# Section 3: Landed Cost
		{"type": "Section Break", "label": "Landed Cost", "link_type": "DocType", "link_to": None, "icon": "receipt-text", "child": 0, "indent": 1, "collapsible": 1},
		{"type": "Link", "label": "Landed Cost Voucher", "link_type": "DocType", "link_to": "Landed Cost Voucher", "icon": "receipt-text", "child": 1, "indent": 0, "collapsible": 1},

		# Section 4: Stock
		{"type": "Section Break", "label": "Stock", "link_type": "DocType", "link_to": None, "icon": "warehouse", "child": 0, "indent": 1, "collapsible": 1},
		{"type": "Link", "label": "Stock Entry", "link_type": "DocType", "link_to": "Stock Entry", "icon": "arrow-left-right", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Warehouse", "link_type": "DocType", "link_to": "Warehouse", "icon": "warehouse", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Item", "link_type": "DocType", "link_to": "Item", "icon": "package", "child": 1, "indent": 0, "collapsible": 1},

		# Section 5: Manufacturing
		{"type": "Section Break", "label": "Manufacturing", "link_type": "DocType", "link_to": None, "icon": "factory", "child": 0, "indent": 1, "collapsible": 1},
		{"type": "Link", "label": "Work Order", "link_type": "DocType", "link_to": "Work Order", "icon": "factory", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Job Card", "link_type": "DocType", "link_to": "Job Card", "icon": "clipboard-list", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Workers (Employees)", "link_type": "DocType", "link_to": "Employee", "icon": "users", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Bill of Materials", "link_type": "DocType", "link_to": "BOM", "icon": "list-tree", "child": 1, "indent": 0, "collapsible": 1},

		# Section 6: Sales
		{"type": "Section Break", "label": "Sales", "link_type": "DocType", "link_to": None, "icon": "storefront", "child": 0, "indent": 1, "collapsible": 1},
		{"type": "Link", "label": "Sales Order", "link_type": "DocType", "link_to": "Sales Order", "icon": "shopping-cart", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Delivery Note", "link_type": "DocType", "link_to": "Delivery Note", "icon": "truck", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Customer", "link_type": "DocType", "link_to": "Customer", "icon": "user-round", "child": 1, "indent": 0, "collapsible": 1},

		# Section 7: Billing
		{"type": "Section Break", "label": "Billing", "link_type": "DocType", "link_to": None, "icon": "credit-card", "child": 0, "indent": 1, "collapsible": 1},
		{"type": "Link", "label": "Sales Invoice", "link_type": "DocType", "link_to": "Sales Invoice", "icon": "receipt-text", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Payment Entry", "link_type": "DocType", "link_to": "Payment Entry", "icon": "credit-card", "child": 1, "indent": 0, "collapsible": 1},

		# Section 8: Reports
		{"type": "Section Break", "label": "Reports", "link_type": "DocType", "link_to": None, "icon": "sheet", "child": 0, "indent": 1, "collapsible": 1},
		{"type": "Link", "label": "Batch Traceability", "link_type": "Report", "link_to": "Chicory Batch Traceability", "icon": "sheet", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Stage Yield & Loss", "link_type": "Report", "link_to": "Chicory Stage Yield and Loss", "icon": "sheet", "child": 1, "indent": 0, "collapsible": 1},
		{"type": "Link", "label": "Stock Ledger", "link_type": "Report", "link_to": "Stock Ledger", "icon": "sheet", "child": 1, "indent": 0, "collapsible": 1},
	]

	if frappe.db.exists("Sidebar", "Cust Chicory Erp"):
		sb = frappe.get_doc("Sidebar", "Cust Chicory Erp")
		sb.items = []
	else:
		sb = frappe.new_doc("Sidebar")
		sb.name = "Cust Chicory Erp"
		sb.title = "Cust Chicory Erp"
		sb.module = "Cust Chicory Erp"
		sb.app = "cust_chicory_erp"
		sb.standard = 1

	for it in items_data:
		sb.append("items", it)

	sb.flags.ignore_permissions = True
	sb.flags.ignore_mandatory = True
	sb.save()
	frappe.cache.delete_key("module_sidebars")


def verify_ui_setup():
	"""Verify number card, dashboard chart, and sidebar structure."""
	from frappe.desk.doctype.number_card.number_card import get_result
	card = frappe.get_doc("Number Card", "Total Raw Roots Inward (Kg)")
	card_val = get_result(card, filters=card.filters_json or [])
	print("✔ Number Card Total Raw Roots Inward (Kg) Result:", card_val)

	from frappe.desk.doctype.dashboard_chart.dashboard_chart import get
	ch_data = get(chart_name="Chicory Root Inward")
	print("✔ Chart Chicory Root Inward Data Labels:", len(ch_data.get("labels", [])))

	from frappe.desk.doctype.sidebar.sidebar import get_sidebar_items
	sb_items = get_sidebar_items("Cust Chicory Erp")
	print("✔ Active Sidebar Items for Cust Chicory Erp:")
	for it in sb_items.get("Cust Chicory Erp", []):
		print(f"   [{it.get('type')}] {it.get('label')} -> {it.get('link_to')}")
	return True
