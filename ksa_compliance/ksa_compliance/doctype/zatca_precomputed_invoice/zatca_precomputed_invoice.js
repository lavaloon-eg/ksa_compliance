// Copyright (c) 2024, LavaLoon and contributors
// For license information, please see license.txt

frappe.ui.form.on("ZATCA Precomputed Invoice", {
    download_xml: function (frm) {
        window.open("/api/method/ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice.download_xml?id=" + frm.doc.name);
    },
});
