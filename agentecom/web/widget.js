/**
 * AgentEcom Storefront Embeddable Chat Widget for Shopify
 * Injectable on any Shopify store theme via:
 * <script src="https://your-domain.com/widget.js" data-api-url="http://localhost:8000" data-shop="yourstore.myshopify.com"></script>
 */

(function () {
    const currentScript = document.currentScript || document.querySelector('script[data-shop]');
    const API_BASE = (currentScript && currentScript.getAttribute('data-api-url')) || window.location.origin;
    const SHOP_DOMAIN = (currentScript && currentScript.getAttribute('data-shop')) || window.location.hostname;

    let sessionId = 'shopper_' + Math.random().toString(36).substring(2, 10);
    let isOpen = false;

    // Inject Widget Styles
    const style = document.createElement('style');
    style.innerHTML = `
        #agentecom-bubble-btn {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4f46e5, #06b6d4);
            color: #ffffff;
            box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 999999;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            border: none;
            outline: none;
        }
        #agentecom-bubble-btn:hover {
            transform: scale(1.08);
            box-shadow: 0 15px 30px -5px rgba(79, 70, 229, 0.5);
        }
        #agentecom-window {
            position: fixed;
            bottom: 96px;
            right: 24px;
            width: 380px;
            height: 580px;
            max-width: calc(100vw - 32px);
            max-height: calc(100vh - 120px);
            border-radius: 20px;
            background: #0f172a;
            color: #f8fafc;
            box-shadow: 0 20px 40px -10px rgba(0,0,0,0.5);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 999999;
            border: 1px solid #1e293b;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        #agentecom-window.open {
            display: flex;
            animation: agentecom-fade-in 0.25s ease-out;
        }
        @keyframes agentecom-fade-in {
            from { opacity: 0; transform: translateY(12px) scale(0.98); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .agentecom-header {
            background: #1e293b;
            padding: 14px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #334155;
        }
        .agentecom-messages {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
            font-size: 13.5px;
            line-height: 1.5;
        }
        .agentecom-msg {
            max-width: 82%;
            padding: 10px 14px;
            border-radius: 14px;
            word-wrap: break-word;
        }
        .agentecom-msg-user {
            align-self: flex-end;
            background: #4f46e5;
            color: #ffffff;
            border-bottom-right-radius: 3px;
        }
        .agentecom-msg-agent {
            align-self: flex-start;
            background: #1e293b;
            color: #e2e8f0;
            border-bottom-left-radius: 3px;
            border: 1px solid #334155;
        }
        .agentecom-card {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 10px;
            margin-top: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .agentecom-checkout-btn {
            background: #06b6d4;
            color: #0f172a;
            font-weight: 600;
            text-align: center;
            padding: 8px;
            border-radius: 8px;
            text-decoration: none;
            margin-top: 4px;
            display: block;
            transition: background 0.2s;
        }
        .agentecom-checkout-btn:hover {
            background: #22d3ee;
        }
        .agentecom-input-bar {
            padding: 12px;
            background: #1e293b;
            border-top: 1px solid #334155;
            display: flex;
            gap: 8px;
        }
        .agentecom-input-bar input {
            flex: 1;
            background: #0f172a;
            border: 1px solid #334155;
            color: #f8fafc;
            padding: 9px 12px;
            border-radius: 10px;
            font-size: 13px;
            outline: none;
        }
        .agentecom-input-bar input:focus {
            border-color: #6366f1;
        }
        .agentecom-input-bar button {
            background: #4f46e5;
            color: #fff;
            border: none;
            padding: 0 14px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 500;
        }
    `;
    document.head.appendChild(style);

    // Create Chat Bubble
    const bubble = document.createElement('button');
    bubble.id = 'agentecom-bubble-btn';
    bubble.innerHTML = `
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
    `;
    document.body.appendChild(bubble);

    // Create Window
    const win = document.createElement('div');
    win.id = 'agentecom-window';
    win.innerHTML = `
        <div class="agentecom-header">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:18px;">🛍️</span>
                <div>
                    <div style="font-weight:600; font-size:13.5px;">Shopping Assistant</div>
                    <div style="font-size:10.5px; color:#94a3b8;">${SHOP_DOMAIN}</div>
                </div>
            </div>
            <button id="agentecom-close-btn" style="background:none; border:none; color:#94a3b8; font-size:18px; cursor:pointer;">&times;</button>
        </div>
        <div class="agentecom-messages" id="agentecom-messages">
            <div class="agentecom-msg agentecom-msg-agent">
                Hi! 👋 I'm your AI shopping assistant for <strong>${SHOP_DOMAIN}</strong>. Ask me anything about products, sizes, tracking, or returns!
            </div>
        </div>
        <div class="agentecom-input-bar">
            <input type="text" id="agentecom-input" placeholder="Ask about products, size swaps, returns..." />
            <button id="agentecom-send-btn">Send</button>
        </div>
    `;
    document.body.appendChild(win);

    // Toggle Window
    bubble.onclick = () => {
        isOpen = !isOpen;
        win.classList.toggle('open', isOpen);
        if (isOpen) document.getElementById('agentecom-input').focus();
    };

    document.getElementById('agentecom-close-btn').onclick = () => {
        isOpen = false;
        win.classList.remove('open');
    };

    // Message Sending Logic
    const msgContainer = document.getElementById('agentecom-messages');
    const input = document.getElementById('agentecom-input');
    const sendBtn = document.getElementById('agentecom-send-btn');

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Render user message
        const userDiv = document.createElement('div');
        userDiv.className = 'agentecom-msg agentecom-msg-user';
        userDiv.textContent = text;
        msgContainer.appendChild(userDiv);
        input.value = '';
        msgContainer.scrollTop = msgContainer.scrollHeight;

        // Loading message
        const agentDiv = document.createElement('div');
        agentDiv.className = 'agentecom-msg agentecom-msg-agent';
        agentDiv.innerHTML = '<span style="color:#94a3b8;">Searching store & thinking...</span>';
        msgContainer.appendChild(agentDiv);
        msgContainer.scrollTop = msgContainer.scrollHeight;

        try {
            const resp = await fetch(`${API_BASE}/api/v1/agent/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId,
                    llm_provider: 'groq'
                })
            });

            if (!resp.ok) throw new Error('Failed to reach assistant server');
            const data = await resp.json();

            let replyHtml = (data.response || '').replace(/\n/g, '<br/>');

            // Render Checkout card if checkout session returned
            if (data.checkout_session) {
                const cs = data.checkout_session;
                const link = cs.checkout_url || `https://${SHOP_DOMAIN}/cart`;
                replyHtml += `
                    <div class="agentecom-card">
                        <div style="font-weight:600; color:#38bdf8;">🛒 Checkout Ready: $${cs.total_amount.toFixed(2)}</div>
                        <a href="${link}" target="_blank" class="agentecom-checkout-btn">👉 Complete Secure Checkout</a>
                    </div>
                `;
            }

            agentDiv.innerHTML = replyHtml;
        } catch (err) {
            agentDiv.innerHTML = `<span style="color:#f87171;">Sorry, couldn't connect right now. Please try again.</span>`;
        }
        msgContainer.scrollTop = msgContainer.scrollHeight;
    }

    sendBtn.onclick = sendMessage;
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
})();
