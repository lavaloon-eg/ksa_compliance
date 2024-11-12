import frappe


def execute():
    print('Start updating old fatoora url')
    sql = """
            SELECT name, fatoora_server_url
            FROM `tabZATCA Business Settings`
         """
    old_urls = frappe.db.sql(sql, as_dict=True)
    fatoora_servers = {'sandbox': 'Sandbox', 'simulation': 'Simulation', 'production': 'Production'}
    print('Updating Fatoora Server based on old urls')
    for url in old_urls:
        fatoora_server_url = url['fatoora_server_url'].strip()
        if fatoora_server_url.startswith('https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal'):
            fatoora_server = fatoora_servers['sandbox']
        elif fatoora_server_url.startswith('https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation'):
            fatoora_server = fatoora_servers['simulation']
        elif fatoora_server_url.startswith('https://gw-fatoora.zatca.gov.sa/e-invoicing/core'):
            fatoora_server = fatoora_servers['production']
        else:
            fatoora_server = None
        if fatoora_server:
            print(f"Setting Fatoora Server for {url['name']} to {fatoora_server}")
            frappe.db.sql(
                """
                            UPDATE `tabZATCA Business Settings` SET fatoora_server = %(fatoora_server)s
                            WHERE name = %(name)s
                            """,
                {'fatoora_server': fatoora_server, 'name': url['name']},
            )
    print('Finish updating Fatoora server for all companies in business settings')
