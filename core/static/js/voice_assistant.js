(function () {
    const button = document.getElementById('voiceAssistantBtn');
    if (!button) {
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition || !('speechSynthesis' in window)) {
        button.hidden = true;
        return;
    }

    const lang = button.dataset.voiceLang || 'ar-MA';
    const apiUrl = button.dataset.voiceApi || '/api/services/';
    const triggers = (button.dataset.voiceTriggers || '')
        .split('|')
        .map((item) => item.trim())
        .filter(Boolean);
    const responsePrefix = button.dataset.voicePrefix || 'Our services include';
    const productsPrefix = button.dataset.voiceProductsPrefix || '';
    const responseSuffix = button.dataset.voiceSuffix || '';
    const fallbackResponse = button.dataset.voiceFallback || 'We offer multiple services to match your needs.';
    const unknownResponse = button.dataset.voiceUnknown || '';
    const joiner = button.dataset.voiceJoiner || ', ';

    let cachedSummary = null;
    let availableVoices = [];

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    function normalize(text) {
        return (text || '')
            .toLowerCase()
            .replace(/[؟?،,!.]/g, '')
            .trim();
    }

    function loadVoices() {
        availableVoices = window.speechSynthesis.getVoices() || [];
    }

    function pickVoice() {
        if (!availableVoices.length) {
            loadVoices();
        }
        return availableVoices.find((voice) => (voice.lang || '').toLowerCase().startsWith('ar')) || null;
    }

    function speak(text) {
        if (!text) {
            return;
        }
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = lang;
        const voice = pickVoice();
        if (voice) {
            utterance.voice = voice;
        }
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }

    async function fetchSummary() {
        if (cachedSummary) {
            return cachedSummary;
        }
        const response = await fetch(apiUrl, {
            headers: { Accept: 'application/json' },
        });
        if (!response.ok) {
            throw new Error('summary fetch failed');
        }
        cachedSummary = await response.json();
        return cachedSummary;
    }

    function buildResponse(summary) {
        const categories = Array.isArray(summary?.categories) ? summary.categories : [];
        const products = Array.isArray(summary?.products) ? summary.products : [];

        const categoryLabels = categories
            .map((item) => item.label || '')
            .filter(Boolean)
            .slice(0, 5);
        const productNames = products
            .map((item) => item.name || '')
            .filter(Boolean)
            .slice(0, 4);

        const parts = [];

        if (categoryLabels.length) {
            parts.push(`${responsePrefix} ${categoryLabels.join(joiner)}`);
        } else if (productNames.length) {
            parts.push(`${responsePrefix} ${productNames.join(joiner)}`);
        }

        if (productNames.length && productsPrefix) {
            parts.push(`${productsPrefix} ${productNames.join(joiner)}`);
        }

        if (responseSuffix) {
            parts.push(responseSuffix);
        }

        return parts.join(' ').trim() || fallbackResponse;
    }

    async function respondWithServices() {
        try {
            const summary = await fetchSummary();
            const response = buildResponse(summary);
            speak(response);
        } catch (error) {
            speak(fallbackResponse);
        }
    }

    function handleTranscript(text) {
        const normalized = normalize(text);
        if (!normalized) {
            return;
        }

        const isMatch = triggers.some((trigger) => {
            if (!trigger) {
                return false;
            }
            return normalized.includes(normalize(trigger));
        });

        if (isMatch) {
            respondWithServices();
        } else if (unknownResponse) {
            speak(unknownResponse);
        }
    }

    recognition.addEventListener('start', () => {
        button.classList.add('is-listening');
        button.setAttribute('aria-pressed', 'true');
    });

    recognition.addEventListener('end', () => {
        button.classList.remove('is-listening');
        button.setAttribute('aria-pressed', 'false');
    });

    recognition.addEventListener('result', (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript || '';
        handleTranscript(transcript);
    });

    recognition.addEventListener('error', () => {
        button.classList.remove('is-listening');
        button.setAttribute('aria-pressed', 'false');
    });

    button.addEventListener('click', () => {
        if (button.classList.contains('is-listening')) {
            recognition.stop();
            return;
        }
        recognition.start();
    });

    if (typeof window.speechSynthesis.onvoiceschanged !== 'undefined') {
        window.speechSynthesis.onvoiceschanged = loadVoices;
    }
    loadVoices();
})();
