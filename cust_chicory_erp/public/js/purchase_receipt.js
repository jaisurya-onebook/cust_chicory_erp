frappe.ui.form.on("Purchase Receipt", {
	gross_weight: function (frm) {
		calculate_weighbridge_weights(frm);
	},
	tare_weight: function (frm) {
		calculate_weighbridge_weights(frm);
	},
	dirt_moisture_deduction_pct: function (frm) {
		calculate_weighbridge_weights(frm);
	},
});

function calculate_weighbridge_weights(frm) {
	const gross = flt(frm.doc.gross_weight);
	const tare = flt(frm.doc.tare_weight);
	let net = 0.0;
	if (gross || tare) {
		net = Math.max(0.0, flt(gross - tare, precision("net_weight", frm.doc)));
	}
	frm.set_value("net_weight", net);

	const deduction_pct = flt(frm.doc.dirt_moisture_deduction_pct);
	let payable = net;
	if (net && deduction_pct) {
		const deduction = flt((net * deduction_pct) / 100.0, precision("net_payable_weight", frm.doc));
		payable = Math.max(0.0, flt(net - deduction, precision("net_payable_weight", frm.doc)));
	}
	frm.set_value("net_payable_weight", payable);
}
