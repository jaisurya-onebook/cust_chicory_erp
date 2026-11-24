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

	if not frappe.flags.in_test:
		print(_("Chicory masters setup completed successfully for company: {0}").format(company))
	return True
