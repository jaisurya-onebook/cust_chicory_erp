import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate

from cust_chicory_erp.controllers.job_card import calculate_job_card_loss
from cust_chicory_erp.controllers.landed_cost import validate_duplicate_freight
from cust_chicory_erp.controllers.quality_gate import validate_batch_quality
from cust_chicory_erp.controllers.weighbridge import calculate_weighbridge_weights


class TestDomainHooks(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.company = "chicory"
		self.item_code = "RAW-CHICORY-ROOT"
		self.supplier = "Chicory Farmer Cooperative"
		self.warehouse = "Raw Material - Cc"
		self.freight_account = "Freight and Forwarding Charges - Cc"

	def test_weighbridge_math(self):
		# 1. Normal calculation with gross, tare, and dirt deduction
		pr = frappe.new_doc("Purchase Receipt")
		pr.gross_weight = 10000.0
		pr.tare_weight = 4000.0
		pr.dirt_moisture_deduction_pct = 5.0
		calculate_weighbridge_weights(pr)

		self.assertEqual(flt(pr.net_weight), 6000.0)
		# 6000 - (6000 * 5%) = 5700
		self.assertEqual(flt(pr.net_payable_weight), 5700.0)

		# 2. Tare weight greater than gross weight -> net weight clamped to 0
		pr.gross_weight = 3000.0
		pr.tare_weight = 4000.0
		pr.dirt_moisture_deduction_pct = 10.0
		calculate_weighbridge_weights(pr)

		self.assertEqual(flt(pr.net_weight), 0.0)
		self.assertEqual(flt(pr.net_payable_weight), 0.0)

		# 3. No dirt deduction (0%)
		pr.gross_weight = 5000.0
		pr.tare_weight = 2000.0
		pr.dirt_moisture_deduction_pct = 0.0
		calculate_weighbridge_weights(pr)

		self.assertEqual(flt(pr.net_weight), 3000.0)
		self.assertEqual(flt(pr.net_payable_weight), 3000.0)

	def test_job_card_loss_math(self):
		jc = frappe.new_doc("Job Card")
		jc.stage_input_qty = 500.0
		jc.stage_output_qty = 475.0
		calculate_job_card_loss(jc)

		self.assertEqual(flt(jc.stage_process_loss_qty), 25.0)

		# Output greater than input -> clamped to 0
		jc.stage_input_qty = 100.0
		jc.stage_output_qty = 110.0
		calculate_job_card_loss(jc)

		self.assertEqual(flt(jc.stage_process_loss_qty), 0.0)

		# Zero input / output
		jc.stage_input_qty = 0.0
		jc.stage_output_qty = 0.0
		calculate_job_card_loss(jc)

		self.assertEqual(flt(jc.stage_process_loss_qty), 0.0)

	def test_quality_gate_blocking_on_hold_batch_stock_entry(self):
		# Create a test batch with On Hold status
		batch = frappe.get_doc({
			"doctype": "Batch",
			"item": self.item_code,
			"batch_id": f"TEST-BATCH-HOLD-{frappe.generate_hash(length=6)}",
			"quality_status": "On Hold",
		}).insert(ignore_permissions=True)

		se = frappe.new_doc("Stock Entry")
		se.purpose = "Material Issue"
		se.company = self.company
		se.append(
			"items",
			{
				"item_code": self.item_code,
				"qty": 10,
				"batch_no": batch.name,
				"s_warehouse": self.warehouse,
			},
		)

		# Should throw ValidationError
		with self.assertRaises(frappe.ValidationError) as cm:
			validate_batch_quality(se)
		self.assertIn("is currently On Hold and cannot be consumed or dispatched", str(cm.exception))

		# Update batch to Rejected -> should also raise ValidationError
		batch.quality_status = "Rejected"
		batch.save()
		with self.assertRaises(frappe.ValidationError) as cm:
			validate_batch_quality(se)
		self.assertIn("is currently Rejected and cannot be consumed or dispatched", str(cm.exception))

		# Update batch to Passed -> should pass without exception
		batch.quality_status = "Passed"
		batch.save()
		try:
			validate_batch_quality(se)
		except frappe.ValidationError:
			self.fail("validate_batch_quality raised ValidationError unexpectedly for Passed batch!")

	def test_quality_gate_blocking_delivery_note(self):
		batch = frappe.get_doc({
			"doctype": "Batch",
			"item": self.item_code,
			"batch_id": f"TEST-BATCH-DN-{frappe.generate_hash(length=6)}",
			"quality_status": "On Hold",
		}).insert(ignore_permissions=True)

		dn = frappe.new_doc("Delivery Note")
		dn.company = self.company
		dn.append(
			"items",
			{
				"item_code": self.item_code,
				"qty": 5,
				"batch_no": batch.name,
				"warehouse": self.warehouse,
			},
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			validate_batch_quality(dn)
		self.assertIn("is currently On Hold and cannot be consumed or dispatched", str(cm.exception))

	def test_duplicate_freight_in_pr_taxes(self):
		# Create a PR with freight tax
		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"company": self.company,
			"supplier": self.supplier,
			"currency": "INR",
			"conversion_rate": 1.0,
			"posting_date": nowdate(),
			"items": [
				{
					"item_code": self.item_code,
					"qty": 100,
					"rate": 50,
					"warehouse": self.warehouse,
				}
			],
			"taxes": [
				{
					"charge_type": "Actual",
					"account_head": self.freight_account,
					"description": "Freight Charges",
					"tax_amount": 500,
					"category": "Valuation and Total",
					"add_deduct_tax": "Add",
				}
			],
		})
		pr.insert(ignore_permissions=True)

		# Create LCV linking this PR with the same freight expense account
		lcv = frappe.new_doc("Landed Cost Voucher")
		lcv.company = self.company
		lcv.posting_date = nowdate()
		lcv.append(
			"purchase_receipts",
			{
				"receipt_document_type": "Purchase Receipt",
				"receipt_document": pr.name,
			},
		)
		lcv.append(
			"taxes",
			{
				"expense_account": self.freight_account,
				"amount": 500,
				"description": "Inward Freight",
			},
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			validate_duplicate_freight(lcv)
		self.assertIn("already contains freight/charges", str(cm.exception))

	def test_duplicate_freight_in_submitted_lcv(self):
		# Create a PR without freight taxes
		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"company": self.company,
			"supplier": self.supplier,
			"currency": "INR",
			"conversion_rate": 1.0,
			"posting_date": nowdate(),
			"items": [
				{
					"item_code": self.item_code,
					"qty": 100,
					"rate": 50,
					"warehouse": self.warehouse,
				}
			],
		})
		pr.flags.ignore_mandatory = True
		pr.flags.ignore_validate = True
		pr.insert(ignore_permissions=True)
		frappe.db.set_value("Purchase Receipt", pr.name, "docstatus", 1)

		# Create and mark submitted a first LCV
		lcv1 = frappe.get_doc({
			"doctype": "Landed Cost Voucher",
			"company": self.company,
			"posting_date": nowdate(),
			"purchase_receipts": [
				{
					"receipt_document_type": "Purchase Receipt",
					"receipt_document": pr.name,
				}
			],
			"taxes": [
				{
					"expense_account": self.freight_account,
					"amount": 1000,
					"description": "Primary Freight",
				}
			],
		})
		lcv1.flags.ignore_validate = True
		lcv1.flags.ignore_mandatory = True
		lcv1.insert(ignore_permissions=True, ignore_mandatory=True)
		frappe.db.set_value("Landed Cost Voucher", lcv1.name, "docstatus", 1)

		# Create second LCV with same PR and same expense account
		lcv2 = frappe.new_doc("Landed Cost Voucher")
		lcv2.company = self.company
		lcv2.posting_date = nowdate()
		lcv2.append(
			"purchase_receipts",
			{
				"receipt_document_type": "Purchase Receipt",
				"receipt_document": pr.name,
			},
		)
		lcv2.append(
			"taxes",
			{
				"expense_account": self.freight_account,
				"amount": 500,
				"description": "Secondary Duplicate Freight",
			},
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			validate_duplicate_freight(lcv2)
		self.assertIn(
			"already has charges capitalized via submitted Landed Cost Voucher", str(cm.exception)
		)
