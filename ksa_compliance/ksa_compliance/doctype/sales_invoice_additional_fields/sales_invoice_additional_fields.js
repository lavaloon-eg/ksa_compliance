// Copyright (c) 2024, Lavaloon and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice Additional Fields", {
    refresh: function (frm) {
        if (frm.doc.integration_status === 'Rejected' && !frm.doc.precomputed_invoice && frm.doc.is_latest) {
            frm.add_custom_button(__('Fix Rejection'), () => fix_rejection(frm), null, 'primary');
        }
    },
    download_xml: function (frm) {
        window.open("/api/method/ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields.download_xml?id=" + frm.doc.name);
    },
});

async function fix_rejection(frm) {
    let invoice_link = `<a target="_blank" href="${frappe.router.make_url(['Form', 'Sales Invoice', frm.doc.sales_invoice])}">${frm.doc.sales_invoice}</a>`
    let message = __("<p>This will create a new Sales Invoice Additional Fields document for the invoice '{0}' and " +
        "submit it to ZATCA. <strong>Make sure you have updated any bad configuration that lead to the initial rejection</strong>.</p>" +
        "<p>Do you want to proceed?</p>", [invoice_link])
    frappe.confirm(message, async () => {
        await frappe.call({
            freeze: true,
            freeze_message: __('Please wait...'),
            method: "ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields.fix_rejection",
            args: {
                id: frm.doc.name,
            },
        });
        // Reload the document to update the 'Is Latest' flag and hide the fix rejection button if we successfully
        // created a new SIAF
        frm.reload_doc();
    }, () => {
    });
}