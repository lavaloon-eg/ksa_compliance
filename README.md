KSA Compliance
--------------

A free and open-source Frappe application for KSA Compliance (ZATCA Integration), offering support for both Phase 1 and Phase 2.

### Main Features

1.  ZATCA Phase 1 - compliance
2.  ZATCA Phase 2 - compliance
3.  Simplified invoice
4.  Standard Invoice
5.  Wizard onboarding
6.  Automatic ZATCA CLI setup
7.  Tax exemption reasons
8.  ZATCA dashboard
9.  Embedded Invoice QR without impacting storage
10. Embedded Invoice XML without impacting storage
11. ZATCA phase 1 print format
12. ZATCA phase 2 print format
13. Resend process
14. Rejection process
15. ZATCA Integration Live and Batch modes
16. Multi-company support
17. Multi-device setup
18. Embedded compliance checks log
19. System XML validation
20. Support ZATCA Sandbox

### How to Install

-   **Frappe Cloud:**\
    One-click installing available if you are hosting on Frappe Cloud
-   **Self Hosting:**

```
bench get-app --branch master https://github.com/lavaloon-eg/ksa_compliance.git
```

```
bench setup requirements
```

```
bench  --site [your.site.name] install-app ksa_compliance
```

```
bench  --site [your.site.name] migrate
```

```
bench restart
```


### Support

### Frappe Cloud:

- If you are hosting on FC premium support is available

### Self Hosting:

- If you need premium support please email: Info@lavaloon.com

### Community Support:

- Available in GitHub discussions <https://github.com/lavaloon-eg/ksa_compliance/discussions>

### New Features and Bug report:

- Please Create Github Issue <https://github.com/lavaloon-eg/ksa_compliance/issues> after checking the existing issues
  - Please include bench information (i.e. output of `bench version`)
  - For invoice rejections, please attach or paste the generated invoice XML (from `Sales Invoice Additional Fields`), any validation warnings/errors, and screenshots of the `Sales Invoice` document
- For paid features, you can email us: <info@lavaloon.com>

### **Contributing**

Will using this the same guidelines from ERPNext

1. [**Issue Guidelines**](https://github.com/frappe/erpnext/wiki/Issue-Guidelines "https://github.com/frappe/erpnext/wiki/issue-guidelines")
2. [**Pull Request Requirements**](https://github.com/frappe/erpnext/wiki/Contribution-Guidelines "https://github.com/frappe/erpnext/wiki/contribution-guidelines")

### License

Copyright (c) 2024 LavaLoon, The KSA Compliance App code is licensed as AGPL
