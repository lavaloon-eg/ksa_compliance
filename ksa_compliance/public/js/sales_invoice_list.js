const standard_settings = frappe.listview_settings['Sales Invoice'] || {};
const standard_onload = standard_settings.onload;

frappe.listview_settings['Sales Invoice'] = {
    ...standard_settings,

    onload(listview) {
        // Call standard ERPNext onload first
        if (standard_onload) {
            standard_onload(listview);
        }

        ksa_compliance.premium_announcement.show_list_announcement_popup(listview);
    }
};