// Audio recording for voice messages
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

const micButton = document.getElementById('micBtn');
const attachButton = document.getElementById('attachBtn');
const fileInput = document.getElementById('fileInput');

// Microphone button
micButton?.addEventListener('click', async () => {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: { 
                    echoCancellation: true, 
                    noiseSuppression: true,
                    autoGainControl: true 
                } 
            });
            
            mediaRecorder = new MediaRecorder(stream, { 
                mimeType: 'audio/webm;codecs=opus' 
            });
            
            audioChunks = [];
            
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    audioChunks.push(e.data);
                }
            };
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                
                // Send voice message via WebSocket
                const reader = new FileReader();
                reader.onload = async (e) => {
                    const conversationId = document.querySelector('#conversation_id').value;
                    const receiverId = document.querySelector('#receiver_id').value;
                    
                    // Create FormData for file upload
                    const formData = new FormData();
                    formData.append('voice_message', audioBlob, 'voice_message.webm');
                    formData.append('receiver_id', receiverId);
                    
                    fetch(`/chat/upload/${conversationId}/`, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        console.log('Voice message sent:', data);
                        // Message will be displayed via WebSocket
                    })
                    .catch(error => console.error('Error sending voice message:', error));
                };
                reader.readAsArrayBuffer(audioBlob);
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
            isRecording = true;
            micButton.classList.add('btn-danger');
            micButton.innerHTML = '<i class="fas fa-stop"></i>';
            micButton.title = 'Stop recording';
        } catch (error) {
            console.error('Microphone access denied:', error);
            alert('Microphone access denied. Please allow microphone access in your browser settings.');
        }
    } else {
        mediaRecorder.stop();
        isRecording = false;
        micButton.classList.remove('btn-danger');
        micButton.innerHTML = '<i class="fas fa-microphone"></i>';
        micButton.title = 'Record audio message';
    }
});

// File upload
attachButton?.addEventListener('click', () => {
    fileInput.click();
});

fileInput?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file && file.size > 50 * 1024 * 1024) {
        alert('File size exceeds 50MB limit');
        return;
    }
    
    if (file) {
        const conversationId = document.querySelector('#conversation_id')?.value;
        const receiverId = document.querySelector('#receiver_id')?.value;
        
        if (!conversationId || !receiverId) {
            console.error('Missing conversation or receiver ID');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('receiver_id', receiverId);
        
        fetch(`/chat/upload/${conversationId}/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('File uploaded:', data);
            addFileMessage(data, file);
        })
        .catch(error => console.error('Error uploading file:', error));
        
        // Reset file input
        fileInput.value = '';
    }
});

function addFileMessage(data, file) {
    const container = document.getElementById('messagesContainer');
    const messageEl = document.createElement('div');
    messageEl.className = 'mb-3 d-flex justify-content-end';
    messageEl.setAttribute('data-message-id', data.message_id);
    
    const fileType = data.file_name.split('.').pop().toLowerCase();
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileType);
    
    let filePreview = '';
    if (isImage) {
        filePreview = `<img src="${data.file_url}" style="max-width:200px;max-height:300px;border-radius:8px;cursor:pointer;" onclick="window.open('${data.file_url}')">`;
    } else if (fileType === 'pdf') {
        filePreview = `<div style="padding:10px;background:#f0f0f0;border-radius:8px;cursor:pointer;" onclick="window.open('${data.file_url}')"><i class="fas fa-file-pdf" style="color:#e74c3c;"></i> ${data.file_name}</div>`;
    } else {
        filePreview = `<div style="padding:10px;background:#f0f0f0;border-radius:8px;cursor:pointer;" onclick="window.open('${data.file_url}')"><i class="fas fa-file"></i> ${data.file_name}</div>`;
    }
    
    messageEl.innerHTML = `
        <div class="chat-bubble p-3 rounded-4" style="background:linear-gradient(90deg,#425ed8,#6067d9);color:#fff;max-width:300px;">
            ${filePreview}
            <div class="mt-2 small text-white-50">just now ✓</div>
        </div>
    `;
    
    container.appendChild(messageEl);
    container.scrollTop = container.scrollHeight;
}

// Emoji picker (simplified)
const emojiBtn = document.getElementById('emojiBtn');
const emojis = ['👍', '❤️', '😂', '😮', '😢', '🔥', '👌', '🎉', '👏', '🙏'];

emojiBtn?.addEventListener('click', (e) => {
    const existing = document.querySelector('.emoji-picker');
    if (existing) {
        existing.remove();
        return;
    }
    
    const picker = document.createElement('div');
    picker.className = 'emoji-picker';
    picker.style.cssText = 'position:absolute;bottom:60px;left:10px;background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px;display:grid;grid-template-columns:repeat(5,40px);gap:5px;box-shadow:0 2px 8px rgba(0,0,0,.1);z-index:1000;';
    
    emojis.forEach(emoji => {
        const span = document.createElement('span');
        span.textContent = emoji;
        span.style.cssText = 'cursor:pointer;font-size:20px;text-align:center;padding:5px;border-radius:4px;transition:background .2s;';
        span.addEventListener('mouseover', () => span.style.background = '#f0f0f0');
        span.addEventListener('mouseout', () => span.style.background = '');
        span.addEventListener('click', () => {
            const messageInput = document.getElementById('messageInput');
            messageInput.value += emoji;
            messageInput.focus();
            picker.remove();
        });
        picker.appendChild(span);
    });
    
    emojiBtn.parentElement.parentElement.insertBefore(picker, emojiBtn.parentElement);
});

// Utility to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

