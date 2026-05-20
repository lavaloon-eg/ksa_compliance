frappe.provide("ksa_compliance.premium_announcement");

ksa_compliance.premium_announcement = {
    open_premium_page() {
        frappe.set_route("ksa-compliance-premium");
    }
};
