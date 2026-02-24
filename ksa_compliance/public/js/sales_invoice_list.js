frappe.listview_settings['Sales Invoice'] = {
    onload(listview) {
        ksa_compliance.premium_announcement.show_announcement(listview)
    }
}