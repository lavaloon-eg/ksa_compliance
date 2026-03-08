frappe.provide("ksa_compliance.premium_announcement");

ksa_compliance.premium_announcement = {
    show_announcement(listview) {
        let announcement_key = "premium_announcement";

        let popup_dismissed = sessionStorage.getItem(announcement_key);

        if (!popup_dismissed) {

            let message = `
                <div style="
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #FFFFFF;
                    color: #000000;
                    padding: 28px;
                    border-radius: 16px;
                    text-align: center;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
                    max-width: 520px;
                    margin: 0 auto;
                ">

                    <div style="font-size: 26px; font-weight: 700; margin-bottom: 16px;">
                        🚀 ${__("Unlock the Full Power of KSA Compliance!")} 🚀
                    </div>
                
                    <div style="
                        font-size: 16px;
                        line-height: 1.7;
                        color: #8a929c;
                        margin-bottom: 22px;
                    ">
                        ${__("Upgrade to our")}
                        <span style="color:#ED1C24; font-weight:600;">
                            &nbsp;${__("Premium version")}&nbsp;
                        </span>
                        ${__("for advanced features; priority support and a seamless compliance experience.")}
                        <br><br>
                        ${__("Take your business to the next level!")} ✨
                    </div>
                
                    <a href="https://lavaloon.com/contact-us"
                       target="_blank"
                       style="
                            display: inline-block;
                            background: linear-gradient(135deg, #22c55e, #16a34a);
                            color: #ffffff;
                            text-decoration: none;
                            padding: 14px 28px;
                            font-size: 16px;
                            font-weight: 600;
                            border-radius: 50px;
                            box-shadow: 0 6px 15px rgba(34,197,94,0.4);
                       ">
                        ${__("Learn More & Contact Us")} &nbsp;📞
                    </a>
                
                </div>
            `;

            frappe.msgprint({
                title: __("KSA Compliance Premium Announcement"),
                message: message,
                indicator: "blue"
            });

            sessionStorage.setItem(announcement_key, "1");
        }
    }
};