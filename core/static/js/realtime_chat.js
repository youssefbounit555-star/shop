(function () {
    const app = document.getElementById('supportChatApp');
    if (!app) {
        return;
    }

    const sendUrl = app.dataset.sendUrl;
    const loadUrl = app.dataset.loadUrl;
    const typingUpdateUrl = app.dataset.typingUpdateUrl;
    const typingGetUrl = app.dataset.typingGetUrl;
    const conversationId = app.dataset.conversationId || '';
    const currentUserId = Number(app.dataset.currentUserId || 0);
    const isAdmin = app.dataset.isAdmin === 'true';
    const pollMs = Number(app.dataset.pollMs || 1200);

    const feed = document.getElementById('supportChatFeed');
    const form = document.getElementById('supportChatForm');
    const textInput = document.getElementById('supportChatText');
    const fileInput = document.getElementById('supportChatFile');
    const recordBtn = document.getElementById('supportChatRecord');
    const clearAudioBtn = document.getElementById('supportChatClearAudio');
    const sendBtn = document.getElementById('supportChatSend');
    const attachmentPreview = document.getElementById('supportChatAttachmentPreview');
    const audioPreviewWrap = document.getElementById('supportChatAudioPreview');
    const audioPreview = document.getElementById('supportChatAudioPlayer');
    const typingNode = document.getElementById('supportChatTyping');

    const knownMessageIds = new Set();
    let lastMessageId = 0;
    let isLoadingMessages = false;
    let recorder = null;
    let recorderStream = null;
    let recorderChunks = [];
    let pendingAudioFile = null;
    let typingTimeout = null;
    let typingState = false;

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    }

    function escapeText(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function formatTime(message) {
        if (message.created_label) {
            return message.created_label;
        }
        if (!message.created_at) {
            return '';
        }
        const dt = new Date(message.created_at);
        if (Number.isNaN(dt.getTime())) {
            return '';
        }
        return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function mediaBlock(message) {
        if (!message.file_url && !message.audio_url) {
            return '';
        }

        let mediaHtml = '<div class="support-media">';

        if (message.file_url) {
            if (message.file_type === 'image') {
                mediaHtml += `<img src="${message.file_url}" alt="attachment">`;
            } else if (message.file_type === 'video') {
                mediaHtml += `<video src="${message.file_url}" controls preload="metadata"></video>`;
            } else {
                const name = escapeText(message.file_name || 'Attachment');
                mediaHtml += (
                    `<a class="support-file-link" href="${message.file_url}" target="_blank" rel="noopener">` +
                    `<i class="fas fa-paperclip"></i> ${name}</a>`
                );
            }
        }

        if (message.audio_url) {
            mediaHtml += `<audio controls src="${message.audio_url}"></audio>`;
        }

        mediaHtml += '</div>';
        return mediaHtml;
    }

    function renderMessage(message, shouldScroll = true) {
        if (!message || !message.id || knownMessageIds.has(message.id)) {
            return;
        }
        knownMessageIds.add(message.id);
        lastMessageId = Math.max(lastMessageId, Number(message.id));

        const isSelf = Number(message.sender_id) === currentUserId;
        const wrapper = document.createElement('article');
        wrapper.className = `support-msg${isSelf ? ' self' : ''}`;
        wrapper.dataset.messageId = String(message.id);

        const senderName = isSelf ? 'You' : (message.sender || 'Support');
        wrapper.innerHTML = (
            `<div class="support-bubble">` +
            `<div class="support-meta">` +
            `<span>${escapeText(senderName)}</span>` +
            `<span>•</span>` +
            `<span>${escapeText(formatTime(message))}</span>` +
            `</div>` +
            (message.text ? `<p class="support-text">${escapeText(message.text)}</p>` : '') +
            mediaBlock(message) +
            `</div>`
        );

        feed.appendChild(wrapper);
        if (shouldScroll) {
            feed.scrollTop = feed.scrollHeight;
        }
    }

    function loadInitialMessages() {
        const initialNode = document.getElementById('supportChatInitialMessages');
        if (!initialNode) {
            return;
        }
        let payload = [];
        try {
            payload = JSON.parse(initialNode.textContent || '[]');
        } catch (error) {
            payload = [];
        }
        payload.forEach((msg) => renderMessage(msg, false));
        feed.scrollTop = feed.scrollHeight;
    }

    function showAttachmentName(file) {
        if (!attachmentPreview) {
            return;
        }
        if (!file) {
            attachmentPreview.textContent = '';
            return;
        }
        attachmentPreview.textContent = `Selected file: ${file.name}`;
    }

    function showAudioPreview(file) {
        if (!audioPreviewWrap || !audioPreview) {
            return;
        }
        if (!file) {
            pendingAudioFile = null;
            audioPreviewWrap.hidden = true;
            clearAudioBtn.hidden = true;
            audioPreview.pause();
            audioPreview.removeAttribute('src');
            return;
        }
        pendingAudioFile = file;
        audioPreview.src = URL.createObjectURL(file);
        audioPreviewWrap.hidden = false;
        clearAudioBtn.hidden = false;
    }

    function appendConversationId(formData) {
        if (isAdmin && conversationId) {
            formData.append('conversation_id', conversationId);
        }
    }

    async function postTypingStatus(isTyping) {
        if (!typingUpdateUrl) {
            return;
        }
        const formData = new FormData();
        formData.append('is_typing', isTyping ? 'true' : 'false');
        appendConversationId(formData);

        await fetch(typingUpdateUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: formData,
        });
    }

    async function pollTypingStatus() {
        if (!typingGetUrl || !typingNode) {
            return;
        }
        const params = new URLSearchParams();
        if (isAdmin && conversationId) {
            params.append('conversation_id', conversationId);
        }
        try {
            const response = await fetch(`${typingGetUrl}?${params.toString()}`);
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            if (payload.is_typing) {
                typingNode.textContent = `${payload.user_name || 'User'} is typing...`;
            } else {
                typingNode.textContent = '';
            }
        } catch (error) {
            // Ignore typing errors silently.
        }
    }

    async function loadNewMessages() {
        if (isLoadingMessages) {
            return;
        }
        isLoadingMessages = true;

        const params = new URLSearchParams();
        params.append('last_message_id', String(lastMessageId || 0));
        if (isAdmin && conversationId) {
            params.append('conversation_id', conversationId);
        }

        try {
            const response = await fetch(`${loadUrl}?${params.toString()}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!response.ok) {
                return;
            }
            const payload = await response.json();
            (payload.messages || []).forEach((msg) => renderMessage(msg));
        } catch (error) {
            // Polling retry is automatic via setInterval.
        } finally {
            isLoadingMessages = false;
        }
    }

    async function sendMessage(event) {
        event.preventDefault();
        const text = (textInput.value || '').trim();
        const file = fileInput.files[0];
        const audio = pendingAudioFile;

        if (!text && !file && !audio) {
            return;
        }

        sendBtn.disabled = true;
        const formData = new FormData();
        formData.append('text', text);
        if (file) {
            formData.append('file', file);
        }
        if (audio) {
            formData.append('audio', audio);
        }
        appendConversationId(formData);

        try {
            const response = await fetch(sendUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: formData,
            });

            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.error || 'Failed to send message.');
            }

            renderMessage(payload);
            textInput.value = '';
            fileInput.value = '';
            showAttachmentName(null);
            showAudioPreview(null);
            await postTypingStatus(false);
            typingState = false;
        } catch (error) {
            window.alert(error.message || 'Failed to send message.');
        } finally {
            sendBtn.disabled = false;
            textInput.focus();
        }
    }

    function releaseRecorderResources() {
        if (recorderStream) {
            recorderStream.getTracks().forEach((track) => track.stop());
            recorderStream = null;
        }
    }

    async function toggleRecording() {
        if (!recordBtn) {
            return;
        }
        if (!window.MediaRecorder || !navigator.mediaDevices) {
            window.alert('Voice recording is not supported in this browser.');
            return;
        }

        if (recorder && recorder.state === 'recording') {
            recorder.stop();
            return;
        }

        try {
            recorderStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            recorderChunks = [];
            recorder = new MediaRecorder(recorderStream);

            recorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    recorderChunks.push(event.data);
                }
            };

            recorder.onstop = () => {
                const blob = new Blob(recorderChunks, { type: 'audio/webm' });
                const file = new File([blob], `voice-${Date.now()}.webm`, { type: 'audio/webm' });
                showAudioPreview(file);
                recordBtn.classList.remove('recording');
                recordBtn.innerHTML = '<i class="fas fa-microphone"></i> Voice';
                releaseRecorderResources();
            };

            recorder.start();
            recordBtn.classList.add('recording');
            recordBtn.innerHTML = '<i class="fas fa-stop"></i> Stop';
        } catch (error) {
            window.alert('Could not access microphone.');
            releaseRecorderResources();
        }
    }

    function wireTyping() {
        if (!textInput || !typingUpdateUrl) {
            return;
        }

        textInput.addEventListener('input', async () => {
            if (!typingState) {
                typingState = true;
                await postTypingStatus(true);
            }
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(async () => {
                typingState = false;
                await postTypingStatus(false);
            }, 850);
        });
    }

    // Init
    loadInitialMessages();
    wireTyping();

    if (form) {
        form.addEventListener('submit', sendMessage);
    }
    if (fileInput) {
        fileInput.addEventListener('change', () => showAttachmentName(fileInput.files[0]));
    }
    if (recordBtn) {
        recordBtn.addEventListener('click', toggleRecording);
    }
    if (clearAudioBtn) {
        clearAudioBtn.addEventListener('click', () => showAudioPreview(null));
    }

    setInterval(loadNewMessages, pollMs);
    setInterval(pollTypingStatus, 1500);

    window.addEventListener('beforeunload', () => {
        if (typingState) {
            postTypingStatus(false);
        }
        releaseRecorderResources();
    });
})();
