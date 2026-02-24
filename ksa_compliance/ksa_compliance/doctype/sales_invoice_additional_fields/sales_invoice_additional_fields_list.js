frappe.listview_settings["Sales Invoice Additional Fields"] = {
    onload(listview) {
        ksa_compliance.premium_announcement.show_announcement(listview)
    }
}