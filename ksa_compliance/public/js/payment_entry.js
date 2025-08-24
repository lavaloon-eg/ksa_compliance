
frappe.ui.form.on('Payment Entry', {

    async refresh(frm) {
        if (frm.doc.custom_prepayment_invoice && frm.doc.docstatus == 1) {
            await set_zatca_integration_status(frm)
        }
    },
})



async function set_zatca_integration_status(frm) {
    const res = await frappe.call({
        method: "ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields.get_zatca_integration_status",
        args: {
            invoice_id: frm.doc.name,
            doctype: frm.doc.doctype
        },
    });

    const status = res.integration_status;
    if (status) {
        let color = "blue"
        if (status === 'Accepted') {
            color = "green"
        } else if (["Rejected", "Resend"].includes(status)) {
            color = "red"
        }
        frm.set_intro(`<b>Zatca Status: ${status}</b>`, color)
    }
}

