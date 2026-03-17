frappe.ui.form.on('Company', {
    refresh(frm) {
        ksa_compliance.premium_announcement.set_announcement_intro(frm)
    }
})