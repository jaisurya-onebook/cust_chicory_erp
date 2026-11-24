import frappe
from frappe.tests import IntegrationTestCase
from cust_chicory_erp.setup.demo_masters import setup_chicory_masters
from cust_chicory_erp.cust_chicory_erp.report.chicory_batch_traceability.chicory_batch_traceability import (
	execute as exec_traceability,
)
from cust_chicory_erp.cust_chicory_erp.report.chicory_stage_yield_and_loss.chicory_stage_yield_and_loss import (
	execute as exec_yield_loss,
)


class TestDemoMastersAndReports(IntegrationTestCase):
	def test_setup_chicory_masters_idempotency(self):
		company = frappe.db.get_single_value("Global Defaults", "default_company") or "chicory"
		# Run twice to test idempotency
		self.assertTrue(setup_chicory_masters(company=company))
		self.assertTrue(setup_chicory_masters(company=company))

		abbr = frappe.get_cached_value("Company", company, "abbr")

		# Verify warehouses
		expected_wh = [
			"Raw Material",
			"Quality Hold",
			"WIP Production",
			"Finished Goods",
			"Packaging Stores",
			"Reject / Scrap",
		]
		for wh_name in expected_wh:
			self.assertTrue(
				frappe.db.exists("Warehouse", f"{wh_name} - {abbr}"),
				f"Warehouse {wh_name} - {abbr} should exist",
			)

		# Verify items
		expected_items = [
			"RAW-CHICORY-ROOT",
			"DRIED-CHICORY",
			"ROASTED-CHICORY",
			"BULK-CHICORY-POWDER",
			"POUCH-1KG",
			"CHICORY-POWDER-1KG",
		]
		for it in expected_items:
			self.assertTrue(frappe.db.exists("Item", it), f"Item {it} should exist")

		# Verify Workstations & Operations
		for ws in ["Root Washer", "Slicer Unit", "Drying Yard", "Rotary Roaster", "Pulverizer Mill", "Automatic Bagging Line"]:
			self.assertTrue(frappe.db.exists("Workstation", ws))

		for op in ["Washing", "Slicing", "Drying", "Roasting", "Grinding & Sieving", "Packing"]:
			self.assertTrue(frappe.db.exists("Operation", op))

		# Verify Routing and Default BOM
		self.assertTrue(frappe.db.exists("Routing", "Chicory Powder Multi-Operation Routing"))
		bom_name = frappe.db.get_value("BOM", {"item": "CHICORY-POWDER-1KG", "is_default": 1})
		self.assertTrue(bom_name)
		bom = frappe.get_doc("BOM", bom_name)
		self.assertEqual(bom.quantity, 100.0)
		self.assertEqual(len(bom.operations), 6)

	def test_chicory_batch_traceability_report(self):
		self.assertTrue(frappe.db.exists("Report", "Chicory Batch Traceability"))
		columns, data, message, chart = exec_traceability({})
		self.assertEqual(len(columns), 9)
		column_fields = [c["fieldname"] for c in columns]
		self.assertIn("finished_batch", column_fields)
		self.assertIn("consumed_raw_batch", column_fields)
		self.assertIn("purchase_receipt", column_fields)
		self.assertIn("supplier", column_fields)
		self.assertIn("landed_cost_rate", column_fields)

	def test_chicory_stage_yield_and_loss_report(self):
		self.assertTrue(frappe.db.exists("Report", "Chicory Stage Yield and Loss"))
		columns, data, message, chart, summary = exec_yield_loss({})
		self.assertEqual(len(columns), 9)
		column_fields = [c["fieldname"] for c in columns]
		self.assertIn("work_order", column_fields)
		self.assertIn("operation", column_fields)
		self.assertIn("input_qty", column_fields)
		self.assertIn("output_qty", column_fields)
		self.assertIn("measured_loss", column_fields)
		self.assertIn("loss_pct", column_fields)
		self.assertIn("loss_reason", column_fields)
		self.assertIn("operator_notes", column_fields)

	def test_chicory_food_manufacturing_workspace(self):
		self.assertTrue(frappe.db.exists("Workspace", "Chicory Food Manufacturing"))
		ws = frappe.get_doc("Workspace", "Chicory Food Manufacturing")
		self.assertEqual(ws.standard, 1)
		self.assertEqual(ws.module, "Cust Chicory Erp")
		self.assertGreaterEqual(len(ws.number_cards), 6)
		self.assertGreaterEqual(len(ws.shortcuts), 8)
		self.assertGreaterEqual(len(ws.links), 20)

	def test_chicory_dashboard_and_components(self):
		from frappe.desk.doctype.sidebar.sidebar import resolve_sidebar

		self.assertTrue(frappe.db.exists("Dashboard", "Chicory Manufacturing"))
		dash = frappe.get_doc("Dashboard", "Chicory Manufacturing")
		self.assertEqual(dash.is_standard, 1)
		self.assertEqual(dash.module, "Cust Chicory Erp")
		self.assertGreaterEqual(len(dash.cards), 6)
		self.assertGreaterEqual(len(dash.charts), 4)

		for ch in [
			"Chicory Root Inward Trends",
			"Chicory Powder Production Output",
			"Chicory Powder Dispatches",
			"Quality Inspection Verdicts",
		]:
			self.assertTrue(frappe.db.exists("Dashboard Chart", ch))

		resolved = resolve_sidebar("Cust Chicory Erp", "Administrator")
		self.assertIsNotNone(resolved)
		first_item = resolved.items[0]
		self.assertEqual(first_item.get("label"), "Dashboard")
		self.assertEqual(first_item.get("link_type"), "Dashboard")
		self.assertEqual(first_item.get("link_to"), "Chicory Manufacturing")

