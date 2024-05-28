// Copyright (c) 2024, LavaLoon and contributors
// For license information, please see license.txt

frappe.ui.form.on("ZATCA Phase 1 Business Settings", {
	company(frm) {
		frappe.call({
			method: "ksa_compliance.ksa_compliance.doctype.zatca_phase_1_business_settings.zatca_phase_1_business_settings.get_company_primary_address",
			args:{
				company: frm.doc.company,
			},
			callback: function (r) {
				console.log(r.message);
				if (r.message.length === 0) {
					frm.set_value("address", "")
				}else{
					frm.set_value("address", r.message[0].name)
				}
			}
		});
	},
});
