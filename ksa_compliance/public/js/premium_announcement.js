frappe.provide("ksa_compliance.premium_announcement");

ksa_compliance.premium_announcement = {
    async show_list_announcement_popup(listview) {
        let announcement_key = "list_announcement_dismiss_date";
        let show_announcement = await this.validate_show_announcement(announcement_key)
        if (!show_announcement) return;
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
                <div style="text-align: center; margin-bottom: 22px">
                    <img src="/assets/ksa_compliance/images/lavaloon_logo.png" alt="lavaloon-logo" width="100">
                </div>
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
            
            </div>`;

            let d = frappe.msgprint({
                title: __("KSA Compliance Premium Announcement"),
                message: message,
                indicator: "blue",
            });
            d.custom_onhide = () => { this.dismiss_announcement(announcement_key) }
    },
    async set_announcement_intro(frm) {
        let announcement_key  = 'frm_announcement_dismiss_date'
        let show_announcement = await this.validate_show_announcement(announcement_key, true)
        let html = `
                        <div id="premimum_annoucement" style="
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                            gap:12px;
                        ">
                            <div style="display:flex; align-items:center; gap:10px; flex:1;">
                        
                                <span style="font-size:12px;"><img src="/assets/ksa_compliance/images/lavaloon_logo.png" alt="lavaloon-logo" width="60"></span>
                        
                                <div style="font-size:12px; line-height:1.6;">
                                    <strong>${__("Unlock the Full Power of KSA Compliance!")}</strong>:
                                    <span style="color:#6b7280;">
                                        ${__("Upgrade to our")}
                                        <span style="color:#ED1C24; font-weight:600;">
                                            ${__("Premium version")}
                                        </span>
                                        ${__("for advanced features; priority support and a seamless compliance experience.")}
                                    </span>
                                </div>
                        
                            </div>
                        
                            <div style="display:flex; align-items:center; gap:8px;">
                        
                                <a href="https://lavaloon.com/contact-us"
                                   target="_blank"
                                   style="
                                        background:#ffffff;
                                        border:1px solid #d7d7d9;
                                        color:#3b3b3b;
                                        text-decoration:none;
                                        padding:2px 6px;
                                        font-size:12px;
                                        border-radius:6px;
                                        font-weight:500;
                                        white-space:nowrap;
                                        margin-right: 20px;
                                   ">
                                   ${__("Learn More")}
                                </a>
                        
                            </div>
                        
                        </div>
                        `
        if (show_announcement) {
            this.custom_set_intro(frm, html, "yellow", () => this.dismiss_announcement(announcement_key));
        }
    },
    async validate_show_announcement(announcement_key, validate_date = false) {
        const show_announcement_res = await frappe.call({
            method: "ksa_compliance.premium_announcement.should_show_announcement",
            args: {
                announcement_key: announcement_key,
                validate_date: validate_date,
            },
        })
        return show_announcement_res.message
    },
    async dismiss_announcement(announcement_key) {
        await frappe.call({
            method: "ksa_compliance.premium_announcement.dismiss_premium_announcement",
            args: {
                announcement_key: announcement_key
            }
        })
    },
    custom_set_intro(frm, html, color, on_dismiss) {
        // This method is copied from frappe/public/js/frappe/form/layout.js show_message() to add on_dismiss functionality
		if (!html) {
			frm.layout.message.empty().addClass("hidden");
			return;
		}

		// Prepare Block
		let $html;
		if (!frappe.utils.is_html(html)) {
			// wrap in a block if `html` does not contain html tags
			$html = $("<div class='form-message'></div>").text(html);
		} else {
			// Wrap in a block just in case the string does not begin with a tag
			// as Jquery assumes it to be a CSS selector and breaks.
			$html = $("<div class='form-message'>").html(html);
		}

		// Add close button to block if not permanent
		const close_message = $(`<div class="close-message">${frappe.utils.icon("close")}</div>`);
        close_message.appendTo($html);
        close_message.on("click", async () => {
            $html.remove()
            await on_dismiss()
        });
		// Add block color and append to parent container `form-message-container`
		const block_color =
			color && ["yellow", "blue", "red", "green", "orange"].includes(color) ? color : "blue";
		$html.addClass(block_color).appendTo(frm.layout.message);

		// Show parent container if hidden
		frm.layout.message.removeClass("hidden");
	}
};