import frappe

def execute():
    print("Start updating old fatoora url")
    sql = """
            SELECT company, fatoora_server_url
            FROM `tabZATCA Business Settings`
        """
    old_urls = frappe.db.sql(sql, as_dict=True)
    new_urls = {
        "sandbox": "Sandbox | https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/",
        "simulation": "Simulation | https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/",
        "production": "Production | https://gw-fatoora.zatca.gov.sa/e-invoicing/core/"
    }
    print("Updating fatoora urls based on old urls")
    for url in old_urls:
        if url["fatoora_server_url"].startswith('https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal'):
            new_url = new_urls["sandbox"]
        elif url["fatoora_server_url"].startswith('https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation'):
            new_url = new_urls["simulation"]
        elif url["fatoora_server_url"].startswith('https://gw-fatoora.zatca.gov.sa/e-invoicing/core'):
            new_url = new_urls["production"]
        else:
            new_url = None
        if new_url:
            frappe.db.sql("""
                            UPDATE `tabZATCA Business Settings` SET fatoora_server_url = %(url)s
                            WHERE company = %(company)s
                            """,
                          {"url": new_url, "company": url["company"]})
    print("Finish updating old fatoora url")

