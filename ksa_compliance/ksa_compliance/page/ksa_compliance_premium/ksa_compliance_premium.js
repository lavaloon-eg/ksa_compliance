frappe.pages["ksa-compliance-premium"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        single_column: true
    });

    page.page = wrapper.page;
    page.page.set_title(__("KSA Compliance Premium"));

    frappe.dom.set_style(`
        .ksa-premium-page {
            max-width: 1080px;
            margin: 0 auto;
            padding: 24px 0 40px;
        }

        .ksa-premium-hero {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 24px;
            padding: 28px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--fg-color);
        }

        .ksa-premium-logo {
            width: 108px;
            margin-bottom: 22px;
        }

        .ksa-premium-hero h1 {
            margin: 0 0 12px;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: 0;
            color: var(--heading-color);
        }

        .ksa-premium-hero p,
        .ksa-premium-grid p,
        .ksa-premium-grid li {
            color: var(--text-muted);
            line-height: 1.6;
        }

        .ksa-premium-hero p {
            max-width: 760px;
            margin: 0;
            font-size: 15px;
        }

        .ksa-premium-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            margin-top: 16px;
        }

        .ksa-premium-grid article {
            padding: 22px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--fg-color);
        }

        .ksa-premium-grid h2 {
            margin: 0 0 8px;
            font-size: 20px;
            font-weight: 650;
            letter-spacing: 0;
            color: var(--heading-color);
        }

        .ksa-premium-grid p {
            margin-bottom: 14px;
        }

        .ksa-premium-grid ul {
            margin: 0;
            padding-left: 18px;
        }

        html[dir="rtl"] .ksa-premium-grid ul {
            padding-left: 0;
            padding-right: 18px;
        }

        @media (max-width: 767px) {
            .ksa-premium-page {
                padding-top: 12px;
            }

            .ksa-premium-hero {
                align-items: flex-start;
                flex-direction: column;
                padding: 20px;
            }

            .ksa-premium-hero h1 {
                font-size: 26px;
            }

            .ksa-premium-grid {
                grid-template-columns: 1fr;
            }
        }
    `);

    const contact_url = "https://lavaloon.com/contact-us";
    const content = `
        <div class="ksa-premium-page">
            <section class="ksa-premium-hero">
                <div>
                    <img src="/assets/ksa_compliance/images/lavaloon_logo.png" alt="LavaLoon" class="ksa-premium-logo">
                    <h1>${__("KSA Compliance Premium")}</h1>
                    <p>
                        ${__("KSA Compliance Community Edition is totally free and includes all core compliance features, including the required ZATCA reports. Premium is an optional upgrade for teams that need deeper insights, advanced reports, and proactive compliance follow-up.")}
                    </p>
                </div>
                <a class="btn btn-primary" href="${contact_url}" target="_blank" rel="noopener">
                    ${__("Contact Us About Premium")}
                </a>
            </section>

            <section class="ksa-premium-grid">
                <article>
                    <h2>${__("Community Edition")}</h2>
                    <p>${__("Included for every KSA Compliance user at no cost.")}</p>
                    <ul>
                        <li>${__("All core KSA Compliance features")}</li>
                        <li>${__("Required compliance reports")}</li>
                        <li>${__("No forced upgrade action")}</li>
                        <li>${__("Continue your daily compliance workflow without interruption")}</li>
                    </ul>
                </article>

                <article>
                    <h2>${__("Premium Edition")}</h2>
                    <p>${__("Available as an optional upgrade for teams with more advanced needs.")}</p>
                    <ul>
                        <li>${__("Deeper compliance insights")}</li>
                        <li>${__("Advanced reporting for review and follow-up")}</li>
                        <li>${__("Proactive compliance enablement")}</li>
                        <li>${__("Additional support for teams managing higher compliance complexity")}</li>
                    </ul>
                </article>
            </section>
        </div>
    `;

    $(content).appendTo(page.main);
};
