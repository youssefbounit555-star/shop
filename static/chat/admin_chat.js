// Admin Chat System - Client-side JavaScript
let currentConversationId = null;
let lastMessageId = 0;
let isLoading = false;
let mediaRecorder = null;
let audioChunks = [];

// Ensure CHAT_URLS is available
if (typeof CHAT_URLS === 'undefined') {
    console.error('CHAT_URLS not defined');
}

document.addEventListener('DOMContentLoaded', function() {
    // Setup conversation list search
    const searchInput = document.getElementById('searchConversations');
    if (searchInput) {
        searchInput.addEventListener('input', filterConversations);
    }
    
    // Setup initial conversation click listeners
    setupConversationClickListeners();
});

function setupConversationClickListeners() {
    const conversationItems = document.querySelectorAll('.conversation-item');
    conversationItems.forEach(item => {
        item.addEventListener('click', function() {
            const conversationId = this.getAttribute('data-conversation-id');
            loadConversation(conversationId);
            
            // Highlight active conversation
            conversationItems.forEach(ci => ci.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function filterConversations() {
    const searchTerm = document.getElementById('searchConversations').value.toLowerCase();
    const conversations = document.querySelectorAll('.conversation-item');
    
    conversations.forEach(conv => {
        const userName = conv.getAttribute('data-user-name').toLowerCase();
        const lastMessage = conv.querySelector('.text-muted');
        const messageText = lastMessage ? lastMessage.textContent.toLowerCase() : '';
        
        if (userName.includes(searchTerm) || messageText.includes(searchTerm)) {
            conv.style.display = '';
        } else {
            conv.style.display = 'none';
        }
    });
}

function loadConversation(conversationId) {
    currentConversationId = conversationId;
    lastMessageId = 0;
    
    // Show right panel
    document.getElementById('inputArea').style.display = 'block';
    document.getElementById('statusBar').style.display = 'flex';
    
    // Clear messages container
    document.getElementById('messagesContainer').innerHTML = '';
    
    // Setup form listeners
    const form = document.getElementById('messageForm');
    if (form) {
        form.removeEventListener('submit', sendMessage);
        form.addEventListener('submit', sendMessage);
    }
    
    document.getElementById('fileBtn')?.removeEventListener('click', triggerFileInput);
    document.getElementById('fileBtn')?.addEventListener('click', triggerFileInput);
    
    document.getElementById('fileInput')?.removeEventListener('change', handleFileSelect);
    document.getElementById('fileInput')?.addEventListener('change', handleFileSelect);
    
    // Load messages
    loadMessages();
    setInterval(loadMessages, 2000);
}

function sendMessage(e) {
    e.preventDefault();
    
    if (!currentConversationId) return;
    
    const text = document.getElementById('messageInput').value.trim();
    if (!text) return;
    
    const formData = new FormData();
    formData.append('text', text);
    formData.append('conversation_id', currentConversationId);
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    fetch(CHAT_URLS.sendMessage, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        
        document.getElementById('messageInput').value = '';
        loadMessages();
        
        // Update conversation list
        updateConversationListOrder();
    })
    .catch(error => console.error('Error:', error));
}

function loadMessages() {
    if (isLoading || !currentConversationId) return;
    isLoading = true;
    
    fetch(`${CHAT_URLS.loadMessages}?conversation_id=${currentConversationId}&last_message_id=${lastMessageId}`)
        .then(response => response.json())
        .then(data => {
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    addMessageToUI(msg);
                    lastMessageId = msg.id;
                });
                // Scroll to bottom
                const container = document.getElementById('messagesContainer');
                container.scrollTop = container.scrollHeight;
            }
        })
        .catch(error => console.error('Error:', error))
        .finally(() => isLoading = false);
}

function addMessageToUI(msg) {
    const container = document.getElementById('messagesContainer');
    
    // Check if message already exists
    if (document.querySelector(`[data-msg-id="${msg.id}"]`)) return;
    
    const messageEl = document.createElement('div');
    messageEl.className = `d-flex mb-4 ${msg.sender_is_admin ? 'justify-content-end' : ''}`;
    messageEl.setAttribute('data-msg-id', msg.id);
    
    let contentHTML = '';
    if (msg.text) {
        contentHTML = `<p class="mb-2" style="margin: 0;">${escapeHtml(msg.text)}</p>`;
    }
    
    if (msg.file_url) {
        const fileType = msg.file_url.split('.').pop().toLowerCase();
        let icon = '<i class="fas fa-file" style="color: #425ed8;"></i>';
        
        if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileType)) {
            contentHTML += `<div class="mt-2">
                <img src="${msg.file_url}" style="max-width: 100%; border-radius: 10px; cursor: pointer;" onclick="window.open('${msg.file_url}')">
            </div>`;
        } else if (fileType === 'pdf') {
            icon = '<i class="fas fa-file-pdf" style="color: #d32f2f;"></i>';
            contentHTML += `<div class="mt-2 p-2" style="background: #e7f3ff; border-radius: 8px; cursor: pointer; display: inline-block;" onclick="window.open('${msg.file_url}')">
                ${icon}
                <strong>${msg.file_name}</strong>
            </div>`;
        } else {
            contentHTML += `<div class="mt-2 p-2" style="background: #e7f3ff; border-radius: 8px; cursor: pointer; display: inline-block;" onclick="window.open('${msg.file_url}')">
                ${icon}
                <strong>${msg.file_name}</strong>
            </div>`;
        }
    }
    
    if (msg.audio_url) {
        contentHTML += `<div class="mt-2">
            <audio controls style="width: 100%; height: 32px; border-radius: 8px;">
                <source src="${msg.audio_url}" type="audio/webm">
            </audio>
        </div>`;
    }
    
    const avatar = msg.sender_is_admin ? 
        `<img src="https://api.dicebear.com/7.x/avataaars/svg?seed=admin" class="rounded-circle ms-2" style="width: 35px; height: 35px; align-self: flex-end;">` :
        `<img src="https://api.dicebear.com/7.x/avataaars/svg?seed=user" class="rounded-circle me-2" style="width: 35px; height: 35px; align-self: flex-end;">`;
    
    messageEl.innerHTML = `
        ${!msg.sender_is_admin ? avatar : ''}
        <div class="chat-bubble" style="max-width: 60%; ${msg.sender_is_admin ? 'background: linear-gradient(135deg, #425ed8, #6067d9); color: white;' : 'background: #f0f0f0; color: #333;'} border-radius: 18px; padding: 12px 16px; word-wrap: break-word;">
            ${contentHTML}
            <small class="${msg.sender_is_admin ? 'text-white-50' : 'text-muted'}" style="display: block; margin-top: 6px;">
                ${new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}
            </small>
        </div>
        ${msg.sender_is_admin ? avatar : ''}
    `;
    
    container.appendChild(messageEl);
}

function sendFileMessage(file) {
    if (!currentConversationId) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', currentConversationId);
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    fetch(CHAT_URLS.sendMessage, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (!data.error) {
            loadMessages();
            updateConversationListOrder();
        }
    });
}

function triggerFileInput() {
    document.getElementById('fileInput').click();
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        if (file.size > 50 * 1024 * 1024) {
            alert('File size exceeds 50MB limit');
            return;
        }
        sendFileMessage(file);
        e.target.value = '';
    }
}

function updateConversationListOrder() {
    // Reload conversation list with updated order and timestamps
    location.reload();
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== Enhanced Features =====

function showQuickReplies() {
    fetch(`${CHAT_URLS.quickReplies}?category=general`)
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('quickRepliesList');
            container.innerHTML = '';
            
            data.replies.forEach(reply => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-sm btn-outline-info d-block w-100 text-start mb-1';
                btn.textContent = reply.title;
                btn.onclick = () => insertQuickReply(reply.message);
                container.appendChild(btn);
            });
            
            document.getElementById('quickRepliesContainer').style.display = 
                data.replies.length > 0 ? 'block' : 'none';
        });
}

function insertQuickReply(message) {
    document.getElementById('messageInput').value = message;
    document.getElementById('quickRepliesContainer').style.display = 'none';
    document.getElementById('messageInput').focus();
}

function updateConversationStatus() {
    const status = document.getElementById('statusSelect').value;
    const priority = document.getElementById('prioritySelect').value;
    
    const formData = new FormData();
    formData.append('conversation_id', currentConversationId);
    formData.append('status', status);
    formData.append('priority', priority);
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    fetch(CHAT_URLS.updateStatus, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Status updated:', data.status, data.priority);
        }
    });
}

// Typing indicator broadcast
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        let typingTimeout;
        messageInput.addEventListener('input', function() {
            // Send typing status
            const formData = new FormData();
            formData.append('conversation_id', currentConversationId);
            formData.append('is_typing', 'true');
            formData.append('csrfmiddlewaretoken', getCsrfToken());
            
            fetch(CHAT_URLS.typing, { method: 'POST', body: formData });
            
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                // Send not typing
                const fd = new FormData();
                fd.append('conversation_id', currentConversationId);
                fd.append('is_typing', 'false');
                fd.append('csrfmiddlewaretoken', getCsrfToken());
                fetch(CHAT_URLS.typing, { method: 'POST', body: fd });
            }, 3000);
        });
    }
});

// Poll typing status every 2 seconds
setInterval(function() {
    if (!currentConversationId) return;
    
    fetch(`${CHAT_URLS.getTyping}?conversation_id=${currentConversationId}`)
        .then(response => response.json())
        .then(data => {
            const indicator = document.getElementById('typingIndicator');
            if (data.is_typing) {
                document.getElementById('typingName').textContent = data.user_name;
                indicator.style.display = 'block';
            } else {
                indicator.style.display = 'none';
            }
        });
}, 2000);
