(function () {
    function init() {
        const root = document.getElementById('globalAiAgentWidget');
        if (!root) {
            return;
        }

        const endpoint = root.dataset.chatEndpoint;
        const defaultAgentId = root.dataset.defaultAgent || 'shop_strategist';

        const promptNode = document.getElementById('globalAgentPromptData');
        const promptMap = promptNode ? JSON.parse(promptNode.textContent) : {};

        const launcher = document.getElementById('globalAiLauncher');
        const panel = document.getElementById('globalAiPanel');
        const closeBtn = document.getElementById('globalAiClose');
        const form = document.getElementById('globalAiForm');
        const input = document.getElementById('globalAiInput');
        const sendBtn = document.getElementById('globalAiSend');
        const feed = document.getElementById('globalAiFeed');
        const promptWrap = document.getElementById('globalAiQuickPrompts');
        const tabs = Array.from(document.querySelectorAll('.ai-widget-agent'));
        const activeName = document.getElementById('globalAiActiveAgentName');
        const activeTagline = document.getElementById('globalAiActiveAgentTagline');

        let selectedAgentId = defaultAgentId;
        let typingNode = null;

        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) {
                return parts.pop().split(';').shift();
            }
            return '';
        }

        function scrollToBottom() {
            feed.scrollTop = feed.scrollHeight;
        }

        function openPanel() {
            if (!panel.hidden) {
                return;
            }
            panel.hidden = false;
            launcher.setAttribute('aria-expanded', 'true');
            setTimeout(() => input.focus(), 70);
        }

        function closePanel() {
            if (panel.hidden) {
                return;
            }
            panel.hidden = true;
            launcher.setAttribute('aria-expanded', 'false');
        }

        function appendMessage(kind, text, recommendations) {
            const article = document.createElement('article');
            article.className = `ai-widget-message ai-widget-message-${kind}`;

            const paragraph = document.createElement('p');
            paragraph.textContent = text;
            article.appendChild(paragraph);

            if (kind === 'assistant' && Array.isArray(recommendations) && recommendations.length) {
                const recoWrap = document.createElement('div');
                recoWrap.className = 'ai-widget-recommendations';

                recommendations.forEach((item) => {
                    const card = document.createElement('div');
                    card.className = 'ai-widget-recommendation';

                    const meta = document.createElement('small');
                    meta.textContent = `${item.name} - ${item.price_label}`;
                    card.appendChild(meta);

                    const link = document.createElement('a');
                    link.href = item.url;
                    link.textContent = 'View product';
                    card.appendChild(link);

                    recoWrap.appendChild(card);
                });

                article.appendChild(recoWrap);
            }

            feed.appendChild(article);
            scrollToBottom();
        }

        function showTyping() {
            if (typingNode) {
                return;
            }

            typingNode = document.createElement('article');
            typingNode.className = 'ai-widget-message ai-widget-message-assistant ai-widget-message-typing';
            const p = document.createElement('p');
            p.textContent = 'Thinking...';
            typingNode.appendChild(p);

            feed.appendChild(typingNode);
            scrollToBottom();
        }

        function hideTyping() {
            if (!typingNode) {
                return;
            }
            typingNode.remove();
            typingNode = null;
        }

        function renderPrompts(agentId) {
            promptWrap.innerHTML = '';
            const prompts = promptMap[agentId] || [];
            prompts.forEach((prompt) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'ai-widget-prompt';
                btn.textContent = prompt;
                btn.addEventListener('click', () => {
                    input.value = prompt;
                    input.focus();
                });
                promptWrap.appendChild(btn);
            });
        }

        function setActiveTab(tab) {
            tabs.forEach((item) => item.classList.remove('is-active'));
            tab.classList.add('is-active');
            selectedAgentId = tab.dataset.agentId;
            activeName.textContent = tab.dataset.agentName;
            activeTagline.textContent = tab.dataset.agentTagline;
            renderPrompts(selectedAgentId);
        }

        async function requestReply(message) {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    agent_id: selectedAgentId,
                    message,
                }),
            });

            const payload = await response.json();
            if (!response.ok || !payload.ok) {
                throw new Error(payload.error || 'Agent error');
            }
            return payload;
        }

        // AI floating icon opens the widget.
        launcher.addEventListener('click', openPanel);

        // X icon closes the widget.
        closeBtn.addEventListener('click', closePanel);

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && !panel.hidden) {
                closePanel();
            }
        });

        document.addEventListener('click', (event) => {
            const openTrigger = event.target.closest('[data-open-ai-widget="true"]');
            if (openTrigger) {
                event.preventDefault();
                openPanel();
                return;
            }

            const clickedInsideWidget = event.target.closest('#globalAiAgentWidget');
            if (!panel.hidden && !clickedInsideWidget) {
                closePanel();
            }
        });

        tabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                setActiveTab(tab);
                appendMessage('assistant', `Switched to ${tab.dataset.agentName}. Tell me your goal.`);
            });
        });

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const message = input.value.trim();
            if (!message) {
                return;
            }

            appendMessage('user', message);
            input.value = '';
            sendBtn.disabled = true;
            showTyping();

            try {
                const payload = await requestReply(message);
                hideTyping();
                appendMessage('assistant', payload.reply, payload.recommendations || []);
            } catch (error) {
                hideTyping();
                appendMessage('assistant', 'Temporary issue. Please try again.');
            } finally {
                sendBtn.disabled = false;
                input.focus();
            }
        });

        const initialTab = tabs.find((tab) => tab.dataset.agentId === defaultAgentId) || tabs[0];
        if (initialTab) {
            setActiveTab(initialTab);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
