// Copyright (c) 2024, Lavaloon and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice Additional Fields", {
    download_xml: function (frm) {
        window.open("/api/method/ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields.download_xml?id=" + frm.doc.name);
    },
});
