// WebSocket connection for real-time chat
const conversationIdEl = document.querySelector('#conversation_id');
const userIdEl = document.querySelector('#user_id');

if (conversationIdEl && userIdEl) {
    const conversationId = conversationIdEl.value;
    const userId = userIdEl.value;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const chatSocket = new WebSocket(
        protocol + '//' + window.location.host + '/ws/chat/' + conversationId + '/'
    );
    
    // Message form handling
    const messageForm = document.getElementById('messageForm');
    messageForm?.addEventListener('submit', (e) => {
        e.preventDefault();
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (message && chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({
                type: 'chat_message',
                message: message,
                receiver_id: document.querySelector('#receiver_id').value
            }));
            messageInput.value = '';
            messageInput.focus();
        }
    });

    // Typing indicator
    const typingTimeout = {};
    const messageInput = document.getElementById('messageInput');
    messageInput?.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({
                type: 'typing',
                is_typing: true
            }));
            
            clearTimeout(typingTimeout.id);
            typingTimeout.id = setTimeout(() => {
                if (chatSocket.readyState === WebSocket.OPEN) {
                    chatSocket.send(JSON.stringify({
                        type: 'typing',
                        is_typing: false
                    }));
                }
            }, 3000);
        }
    });
    
    messageInput?.addEventListener('blur', () => {
        if (chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({
                type: 'typing',
                is_typing: false
            }));
        }
    });

    // WebSocket events
    chatSocket.onopen = (e) => {
        console.log('Chat socket opened');
    };

    chatSocket.onmessage = (e) => {
        const data = JSON.parse(e.data);
        
        if (data.type === 'chat_message') {
            addMessageToChat(data);
        } else if (data.type === 'typing_indicator') {
            showTypingIndicator(data);
        } else if (data.type === 'message_reaction') {
            updateReaction(data);
        } else if (data.type === 'message_edited') {
            updateEditedMessage(data);
        } else if (data.type === 'message_deleted') {
            deleteMessage(data);
        } else if (data.type === 'user_status_change') {
            updateUserStatus(data);
        } else if (data.type === 'message_read') {
            updateMessageStatus(data);
        }
    };

    chatSocket.onerror = (error) => {
        console.error('Chat socket error:', error);
    };

    chatSocket.onclose = (e) => {
        console.log('Chat socket closed');
    };

    // Add message to chat
    function addMessageToChat(data) {
        const container = document.getElementById('messagesContainer');
        const isOwn = parseInt(data.sender_id) === parseInt(userId);
        const messageEl = document.createElement('div');
        messageEl.className = `d-flex mb-3 ${isOwn ? 'justify-content-end' : ''}`;
        messageEl.setAttribute('data-message-id', data.message_id);
        
        const timestamp = new Date(data.timestamp);
        const timeString = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageEl.innerHTML = `
            <div class="chat-bubble p-3 rounded-4" style="max-width:60%;background:${isOwn ? 'linear-gradient(90deg,#425ed8,#6067d9)' : '#f0f0f0'};color:${isOwn ? '#fff' : '#000'};position:relative;word-break:break-word;" oncontextmenu="showMessageMenu(event, ${data.message_id}, ${isOwn})">
                <div class="mb-1 small ${isOwn ? 'text-white-50' : 'text-muted'}">${data.sender_username}</div>
                <div>${escapeHtml(data.content)}</div>
                <div class="mt-1 small ${isOwn ? 'text-white-50' : 'text-muted'}">
                    ${timeString}
                    ${isOwn ? '<span title="Delivered">✓✓</span>' : ''}
                </div>
            </div>
        `;
        container.appendChild(messageEl);
        container.scrollTop = container.scrollHeight;
    }

    // Show typing indicator
    function showTypingIndicator(data) {
        const typingEl = document.getElementById('typingIndicator');
        if (data.is_typing && parseInt(data.user_id) !== parseInt(userId)) {
            if (!typingEl) {
                const container = document.getElementById('messagesContainer');
                const ind = document.createElement('div');
                ind.id = 'typingIndicator';
                ind.className = 'mb-3';
                ind.style.color = '#999';
                ind.innerHTML = `<p class="text-muted small mb-0"><em>${data.username} is typing...</em></p>`;
                container.appendChild(ind);
            }
        } else if (typingEl && !data.is_typing) {
            typingEl.remove();
        }
    }

    // Update reaction
    function updateReaction(data) {
        const messageEl = document.querySelector(`[data-message-id="${data.message_id}"] .chat-bubble`);
        if (messageEl) {
            if (data.action === 'add') {
                if (!messageEl.querySelector('.reactions')) {
                    const reactionsDiv = document.createElement('div');
                    reactionsDiv.className = 'reactions mt-2 d-flex gap-1 flex-wrap';
                    messageEl.appendChild(reactionsDiv);
                }
                messageEl.querySelector('.reactions').innerHTML += `<span class="badge bg-light text-dark small" onclick="removeReaction(${data.message_id}, '${data.emoji}')">${data.emoji}</span>`;
            } else if (data.action === 'remove') {
                const badges = messageEl.querySelectorAll('.badge');
                badges.forEach(b => {
                    if (b.textContent.trim() === data.emoji) b.remove();
                });
            }
        }
    }

    // Update edited message
    function updateEditedMessage(data) {
        const messageEl = document.querySelector(`[data-message-id="${data.message_id}"] .chat-bubble`);
        if (messageEl) {
            const contentDiv = messageEl.querySelector('div:nth-child(2)');
            if (contentDiv) {
                contentDiv.textContent = data.new_content;
                const editLabel = messageEl.innerHTML.includes('(edited)') ? '' : ' (edited)';
                if (!editLabel) messageEl.innerHTML += '<span class="small text-muted"> (edited)</span>';
            }
        }
    }

    // Delete message
    function deleteMessage(data) {
        if (data.deleted_for === 'everyone') {
            const messageEl = document.querySelector(`[data-message-id="${data.message_id}"]`);
            if (messageEl) {
                messageEl.style.opacity = '0.5';
                const bubble = messageEl.querySelector('.chat-bubble');
                if (bubble) bubble.textContent = 'This message was deleted';
            }
        }
    }

    // Update message status
    function updateMessageStatus(data) {
        const messageEl = document.querySelector(`[data-message-id="${data.message_id}"] .chat-bubble`);
        if (messageEl) {
            const statusEl = messageEl.querySelector('.mt-1');
            if (statusEl) statusEl.innerHTML = statusEl.innerHTML.replace('✓', '✓✓');
        }
    }

    // Update user status
    function updateUserStatus(data) {
        const statusEl = document.querySelector('[data-user-id="' + data.user_id + '"]');
        if (statusEl) {
            statusEl.innerHTML = data.is_online ? 
                '<span style="color:#43a047;">● Online</span>' : 
                'Last seen just now';
        }
    }

    // Helper function to escape HTML
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    // Message menu
    window.showMessageMenu = function(event, messageId, isOwn) {
        event.preventDefault();
        const existing = document.querySelector('.message-menu');
        if (existing) existing.remove();
        
        const menu = document.createElement('div');
        menu.className = 'message-menu';
        menu.innerHTML = `
            <a class="react-btn" onclick="showEmojiPicker(${messageId})">👍 React</a>
            ${isOwn ? `<a onclick="editMessage(${messageId})">✏️ Edit</a>` : ''}
            ${isOwn ? `<a onclick="deleteMessage(${messageId}, 'everyone')">🗑️ Delete</a>` : ''}
            <a onclick="copyMessage('${messageId}')">📋 Copy</a>
        `;
        event.target.parentElement.appendChild(menu);
    };

    // Global functions
    window.removeReaction = function(messageId, emoji) {
        if (chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({
                type: 'reaction',
                message_id: messageId,
                emoji: emoji,
                action: 'remove'
            }));
        }
    };
}

