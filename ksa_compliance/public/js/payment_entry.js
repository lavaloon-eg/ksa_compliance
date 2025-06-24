
frappe.ui.form.on('Payment Entry', {

    async refresh(frm) {
        if (frm.doc.custom_prepayment_invoice && frm.doc.docstatus == 1) {
            await set_zatca_integration_status(frm)
        }
    },
})



async function set_zatca_integration_status(frm) {
    const res = await frappe.db.get_value("Sales Invoice Additional Fields", {
        "sales_invoice": frm.doc.name,
        "is_latest": 1
    }, "integration_status");
    const status = res.message.integration_status
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

