frappe.listview_settings["ZATCA Phase 1 Business Settings"] = {
    onload(listview) {
        ksa_compliance.premium_announcement.show_list_announcement_popup(listview)
    }
}