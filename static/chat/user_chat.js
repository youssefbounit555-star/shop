// User Chat System - Client-side JavaScript
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
    console.log('✓ DOM loaded, initializing chat...');
    
    const conversationId = document.getElementById('conversationId');
    if (!conversationId) {
        console.error('❌ conversationId element not found');
        return;
    }
    
    currentConversationId = conversationId.value;
    console.log('✓ Conversation ID:', currentConversationId);
    console.log('✓ CHAT_URLS:', CHAT_URLS);
    
    // Setup event listeners
    const messageForm = document.getElementById('messageForm');
    const fileBtn = document.getElementById('fileBtn');
    const fileInput = document.getElementById('fileInput');
    const micBtn = document.getElementById('micBtn');
    const messageInput = document.getElementById('messageInput');
    
    if (!messageForm) console.error('❌ messageForm not found');
    if (!fileBtn) console.error('❌ fileBtn not found');
    if (!micBtn) console.error('❌ micBtn not found');
    if (!messageInput) console.error('❌ messageInput not found');
    
    if (messageForm) messageForm.addEventListener('submit', sendMessage);
    if (fileBtn) fileBtn.addEventListener('click', triggerFileInput);
    if (fileInput) fileInput.addEventListener('change', handleFileSelect);
    if (micBtn) micBtn.addEventListener('click', toggleRecording);
    if (messageInput) messageInput.addEventListener('input', handleTyping);
    
    console.log('✓ Event listeners attached');
    
    // Load messages periodically (long polling)
    loadMessages();
    setInterval(loadMessages, 2000);
    
    // Update unread count
    updateUnreadCount();
    setInterval(updateUnreadCount, 5000);
});

function sendMessage(e) {
    e.preventDefault();
    console.log('✓ sendMessage called');
    
    const messageInput = document.getElementById('messageInput');
    const text = messageInput.value.trim();
    
    console.log('✓ Message text:', text);
    console.log('✓ Conversation ID:', currentConversationId);
    
    if (!text) {
        console.warn('⚠️ Message is empty, not sending');
        return;
    }
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (!csrfToken) {
        console.error('❌ CSRF token not found');
        alert('Security token missing');
        return;
    }
    
    const formData = new FormData();
    formData.append('text', text);
    formData.append('conversation_id', currentConversationId);
    formData.append('csrfmiddlewaretoken', csrfToken.value);
    
    console.log('✓ FormData prepared, sending to:', CHAT_URLS.sendMessage);
    
    fetch(CHAT_URLS.sendMessage, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin'
    })
    .then(response => {
        console.log('✓ Response received, status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('✓ Response JSON:', data);
        
        if (data.error) {
            console.error('❌ API Error:', data.error);
            alert('Error: ' + data.error);
            return;
        }
        
        console.log('✓ Message sent successfully, ID:', data.id);
        messageInput.value = '';
        loadMessages();
    })
    .catch(error => {
        console.error('❌ Fetch error:', error);
        alert('Error sending message: ' + error.message);
    });
}

function loadMessages() {
    if (isLoading) return;
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
    
    const isCurrentUser = msg.sender_id === parseInt(document.querySelector('[name=csrfmiddlewaretoken]').parentElement.getAttribute('data-user-id') || '0');
    
    const messageEl = document.createElement('div');
    messageEl.className = `d-flex mb-4 ${!msg.sender_is_admin ? 'justify-content-end' : ''}`;
    messageEl.setAttribute('data-msg-id', msg.id);
    
    let contentHTML = '';
    if (msg.text) {
        contentHTML = `<p class="mb-2" style="margin: 0;">${escapeHtml(msg.text)}</p>`;
    }
    
    if (msg.file_url) {
        const icon = msg.file_type === 'image' ? 
            `<img src="${msg.file_url}" style="max-width: 100%; border-radius: 10px; cursor: pointer;" onclick="window.open('${msg.file_url}')">` :
            `<div class="p-2" style="background: #e7f3ff; border-radius: 8px; cursor: pointer; display: inline-block;" onclick="window.open('${msg.file_url}')">
                <i class="fas fa-file me-2" style="color: #425ed8;"></i>
                <strong>${msg.file_name}</strong>
            </div>`;
        contentHTML += `<div class="mt-2">${icon}</div>`;
    }
    
    if (msg.audio_url) {
        contentHTML += `<div class="mt-2">
            <audio controls style="width: 100%; height: 32px; border-radius: 8px;">
                <source src="${msg.audio_url}" type="audio/webm">
            </audio>
        </div>`;
    }
    
    const avatar = msg.sender_is_admin ? 
        `<img src="https://api.dicebear.com/7.x/avataaars/svg?seed=admin" class="rounded-circle me-2" style="width: 35px; height: 35px; align-self: flex-end;">` :
        '';
    
    const avatarRight = !msg.sender_is_admin ? 
        `<img src="https://api.dicebear.com/7.x/avataaars/svg?seed=user" class="rounded-circle ms-2" style="width: 35px; height: 35px; align-self: flex-end;">` :
        '';
    
    messageEl.innerHTML = `
        ${avatar}
        <div class="chat-bubble" style="max-width: 60%; ${!msg.sender_is_admin ? 'background: linear-gradient(135deg, #425ed8, #6067d9); color: white;' : 'background: #f0f0f0; color: #333;'} border-radius: 18px; padding: 12px 16px; word-wrap: break-word;">
            ${contentHTML}
            <small class="${!msg.sender_is_admin ? 'text-white-50' : 'text-muted'}" style="display: block; margin-top: 6px;">
                ${new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}
            </small>
        </div>
        ${avatarRight}
    `;
    
    container.appendChild(messageEl);
}

function sendFileMessage(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', currentConversationId);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    
    fetch(CHAT_URLS.sendMessage, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (!data.error) {
            loadMessages();
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

async function toggleRecording() {
    const btn = document.getElementById('micBtn');
    
    if (!mediaRecorder) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            audioChunks = [];
            
            mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const formData = new FormData();
                formData.append('audio', audioBlob, 'message.webm');
                formData.append('conversation_id', currentConversationId);
                formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
                
                fetch(CHAT_URLS.sendMessage, {
                    method: 'POST',
                    body: formData
                }).then(response => response.json()).then(data => {
                    if (!data.error) loadMessages();
                });
                
                stream.getTracks().forEach(track => track.stop());
                mediaRecorder = null;
            };
            
            mediaRecorder.start();
            btn.classList.add('btn-danger');
            btn.innerHTML = '<i class="fas fa-stop"></i>';
        } catch (error) {
            alert('Microphone access denied');
        }
    } else {
        mediaRecorder.stop();
        btn.classList.remove('btn-danger');
        btn.innerHTML = '<i class="fas fa-microphone"></i>';
    }
}

function handleTyping() {
    // You can add typing indicator here if needed
    document.getElementById('typingIndicator').style.display = 'none';
}

function updateUnreadCount() {
    fetch(CHAT_URLS.getUnreadCount)
        .then(response => response.json())
        .then(data => {
            const badge = document.querySelector('[data-unread-badge]');
            if (badge) {
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.parentElement.style.display = 'block';
                } else {
                    badge.parentElement.style.display = 'none';
                }
            }
        });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
