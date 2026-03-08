(function () {
    const root = document.getElementById('agentsPageRoot');
    if (!root) {
        return;
    }

    const endpoint = root.dataset.chatEndpoint;
    const defaultAgent = root.dataset.defaultAgent;
    const promptDataNode = document.getElementById('agentPromptsData');
    const promptMap = promptDataNode ? JSON.parse(promptDataNode.textContent) : {};

    const cards = Array.from(document.querySelectorAll('.agent-card'));
    const activeAgentName = document.getElementById('activeAgentName');
    const activeAgentTagline = document.getElementById('activeAgentTagline');
    const promptContainer = document.getElementById('agentPromptChips');
    const form = document.getElementById('agentChatForm');
    const input = document.getElementById('agentMessageInput');
    const sendBtn = document.getElementById('agentSendBtn');
    const feed = document.getElementById('agentMessageFeed');
    const csrfInput = form ? form.querySelector('input[name="csrfmiddlewaretoken"]') : null;

    let selectedAgentId = defaultAgent;
    let typingNode = null;

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    }

    function scrollFeedToBottom() {
        feed.scrollTop = feed.scrollHeight;
    }

    function appendMessage(kind, text, recommendations) {
        const article = document.createElement('article');
        article.className = `message message-${kind}`;

        const body = document.createElement('div');
        body.className = 'message-body';
        const paragraph = document.createElement('p');
        paragraph.textContent = text;
        body.appendChild(paragraph);

        if (kind === 'assistant' && Array.isArray(recommendations) && recommendations.length) {
            const recoWrap = document.createElement('div');
            recoWrap.className = 'recommendation-cards';

            recommendations.forEach((item) => {
                const card = document.createElement('div');
                card.className = 'recommendation-card';

                const title = document.createElement('h4');
                title.textContent = item.name;
                card.appendChild(title);

                const category = document.createElement('p');
                category.textContent = item.category;
                card.appendChild(category);

                const meta = document.createElement('div');
                meta.className = 'recommendation-meta';

                const price = document.createElement('strong');
                price.textContent = item.price_label;
                meta.appendChild(price);

                const viewLink = document.createElement('a');
                viewLink.className = 'recommendation-link';
                viewLink.href = item.url;
                viewLink.textContent = 'View Product';
                meta.appendChild(viewLink);

                card.appendChild(meta);
                recoWrap.appendChild(card);
            });

            body.appendChild(recoWrap);
        }

        article.appendChild(body);
        feed.appendChild(article);
        scrollFeedToBottom();
    }

    function showTyping() {
        if (typingNode) {
            return;
        }
        typingNode = document.createElement('article');
        typingNode.className = 'message message-assistant message-typing';

        const body = document.createElement('div');
        body.className = 'message-body';
        const paragraph = document.createElement('p');
        paragraph.textContent = 'Agent is thinking...';
        body.appendChild(paragraph);
        typingNode.appendChild(body);

        feed.appendChild(typingNode);
        scrollFeedToBottom();
    }

    function hideTyping() {
        if (!typingNode) {
            return;
        }
        typingNode.remove();
        typingNode = null;
    }

    function renderPromptChips(agentId) {
        promptContainer.innerHTML = '';
        const prompts = promptMap[agentId] || [];
        prompts.forEach((prompt) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'quick-prompt-btn';
            btn.textContent = prompt;
            btn.addEventListener('click', () => {
                input.value = prompt;
                input.focus();
            });
            promptContainer.appendChild(btn);
        });
    }

    function setActiveAgent(card) {
        cards.forEach((entry) => entry.classList.remove('is-active'));
        card.classList.add('is-active');

        selectedAgentId = card.dataset.agentId;
        activeAgentName.textContent = card.dataset.agentName;
        activeAgentTagline.textContent = card.dataset.agentTagline;
        renderPromptChips(selectedAgentId);
    }

    async function requestReply(message) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || (csrfInput ? csrfInput.value : ''),
            },
            body: JSON.stringify({
                agent_id: selectedAgentId,
                message,
            }),
        });

        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            throw new Error(payload.error || 'Failed to generate response.');
        }
        return payload;
    }

    cards.forEach((card) => {
        card.addEventListener('click', () => {
            setActiveAgent(card);
            appendMessage('assistant', `Switched to ${card.dataset.agentName}. Tell me what you want to achieve.`);
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
            appendMessage('assistant', 'I hit a temporary issue. Please try again in a moment.');
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    });

    const initialCard = cards.find((card) => card.dataset.agentId === defaultAgent) || cards[0];
    if (initialCard) {
        setActiveAgent(initialCard);
    }
})();
