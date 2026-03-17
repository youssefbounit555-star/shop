(() => {
    const modal = document.getElementById('chooseHelperModal');
    if (!modal) {
        return;
    }

    const storeUrl = modal.getAttribute('data-store-url') || '/store/';
    const openButtons = document.querySelectorAll('[data-choose-helper-open]');
    const closeButtons = modal.querySelectorAll('[data-choose-helper-close]');
    const backBtn = document.getElementById('chooseHelperBack');
    const nextBtn = document.getElementById('chooseHelperNext');
    const resultEl = document.getElementById('chooseHelperResult');
    const resultLink = document.getElementById('chooseHelperLink');
    const seeAllLink = document.getElementById('chooseHelperSeeAll');
    const panels = Array.from(modal.querySelectorAll('.choose-helper-panel'));
    const progressDots = Array.from(modal.querySelectorAll('.choose-helper-progress span'));
    const questionContainers = {
        project: modal.querySelector('[data-question="project"]'),
        budget: modal.querySelector('[data-question="budget"]'),
        audience: modal.querySelector('[data-question="audience"]'),
    };

    const storageKeys = {
        catalog: 'chooseHelperCatalog',
        pending: 'chooseHelperPending',
    };

    let catalog = [];
    let stepIndex = 0;
    let answers = {};
    let categoryValues = new Set();

    const initAnswers = () => {
        answers = {
            project: 'any',
            budget: null,
            audience: null,
        };
    };

    const parseNumber = (value) => {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : 0;
    };

    const getCurrencyLabel = () => {
        const storePage = document.querySelector('.store-page');
        if (storePage) {
            return storePage.getAttribute('data-currency') || 'USD';
        }
        const geoProfileEl = document.getElementById('geoProfileData');
        if (geoProfileEl) {
            try {
                const geoProfile = JSON.parse(geoProfileEl.textContent);
                return geoProfile.currency_label || geoProfile.currency || 'USD';
            } catch (error) {
                return 'USD';
            }
        }
        return 'USD';
    };

    const buildCatalogFromCards = () => {
        const cards = Array.from(document.querySelectorAll('.product-card'));
        if (!cards.length) {
            return [];
        }
        return cards.map((card) => ({
            id: card.getAttribute('data-id') || '',
            name: card.getAttribute('data-name') || '',
            category: card.getAttribute('data-category') || '',
            categoryLabel: card.getAttribute('data-category-label') || '',
            price: parseNumber(card.getAttribute('data-price')),
            oldPrice: parseNumber(card.getAttribute('data-old-price')),
            description: card.getAttribute('data-description') || '',
            image: card.getAttribute('data-image') || '',
            url: card.getAttribute('data-url') || '#',
            inStock: card.getAttribute('data-in-stock') === '1',
            discount: parseNumber(card.getAttribute('data-discount')),
            featured: card.getAttribute('data-featured') === '1',
        })).filter((item) => item.id && item.name);
    };

    const readStorage = (key) => {
        try {
            const raw = window.localStorage.getItem(key);
            if (!raw) {
                return null;
            }
            return JSON.parse(raw);
        } catch (error) {
            return null;
        }
    };

    const writeStorage = (key, payload) => {
        try {
            window.localStorage.setItem(key, JSON.stringify(payload));
        } catch (error) {
            return;
        }
    };

    const loadCatalog = () => {
        const cardsCatalog = buildCatalogFromCards();
        if (cardsCatalog.length) {
            writeStorage(storageKeys.catalog, cardsCatalog.slice(0, 80));
            return cardsCatalog;
        }
        const stored = readStorage(storageKeys.catalog);
        if (Array.isArray(stored) && stored.length) {
            return stored;
        }
        return [];
    };

    const buildProjectOptions = (items) => {
        const map = new Map();
        items.forEach((item) => {
            if (!item.category) {
                return;
            }
            if (!map.has(item.category)) {
                map.set(item.category, item.categoryLabel || item.category);
            }
        });
        categoryValues = new Set(map.keys());
        const options = [];
        if (map.size) {
            options.push({ value: 'any', label: 'غير محدد' });
            Array.from(map.entries()).slice(0, 6).forEach(([value, label]) => {
                options.push({ value, label });
            });
            return options;
        }
        return [
            { value: 'any', label: 'غير محدد' },
            { value: 'ecommerce', label: 'متجر إلكتروني' },
            { value: 'restaurant', label: 'مطعم أو كافيه' },
            { value: 'beauty', label: 'صالون أو عناية' },
            { value: 'agency', label: 'شركة أو وكالة' },
            { value: 'education', label: 'تعليم أو تدريب' },
            { value: 'other', label: 'غير ذلك' },
        ];
    };

    const buildBudgetOptions = () => {
        const currency = getCurrencyLabel();
        return [
            { key: 'under_50', min: 0, max: 50, label: `أقل من 50 ${currency}` },
            { key: '50_200', min: 50, max: 200, label: `من 50 إلى 200 ${currency}` },
            { key: '200_500', min: 200, max: 500, label: `من 200 إلى 500 ${currency}` },
            { key: 'over_500', min: 500, max: null, label: `أكثر من 500 ${currency}` },
        ];
    };

    const audienceOptions = [
        { value: 'women', label: 'للنساء' },
        { value: 'men', label: 'للرجال' },
        { value: 'kids', label: 'للأطفال' },
        { value: 'simple', label: 'ستايل بسيط' },
    ];

    const projectKeywords = {
        ecommerce: ['متجر', 'تجارة', 'shop', 'store', 'ecommerce', 'online'],
        restaurant: ['مطعم', 'كاف', 'cafe', 'restaurant', 'food', 'coffee', 'tea'],
        beauty: ['صالون', 'تجميل', 'beauty', 'salon', 'spa', 'hair', 'makeup'],
        agency: ['شركة', 'وكالة', 'agency', 'marketing', 'تسويق', 'business', 'brand'],
        education: ['تعليم', 'تدريب', 'course', 'academy', 'education', 'مدرس', 'تعليمي'],
        other: [],
    };

    const audienceKeywords = {
        women: ['نساء', 'نسائي', 'woman', 'women', 'female', 'girl', 'girls', 'ladies'],
        men: ['رجال', 'رجالي', 'man', 'men', 'male', 'gents', 'mens'],
        kids: ['أطفال', 'طفل', 'kids', 'kid', 'children', 'baby', 'babies', 'toddler'],
        simple: ['بسيط', 'minimal', 'basic', 'clean', 'simple'],
    };

    const renderOptions = (questionId, options) => {
        const container = questionContainers[questionId];
        if (!container) {
            return;
        }
        container.innerHTML = '';
        options.forEach((option) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'choose-helper-option';
            button.dataset.question = questionId;
            button.dataset.value = option.value || option.key || '';
            if (option.min !== undefined) {
                button.dataset.min = option.min;
            }
            if (option.max !== undefined && option.max !== null) {
                button.dataset.max = option.max;
            }
            button.textContent = option.label;
            if (questionId === 'project' && answers.project === option.value) {
                button.classList.add('is-selected');
            }
            if (questionId === 'budget' && answers.budget && answers.budget.key === option.key) {
                button.classList.add('is-selected');
            }
            if (questionId === 'audience' && answers.audience === option.value) {
                button.classList.add('is-selected');
            }
            container.appendChild(button);
        });
    };

    const renderQuestions = () => {
        renderOptions('project', buildProjectOptions(catalog));
        renderOptions('budget', buildBudgetOptions());
        renderOptions('audience', audienceOptions);
    };

    const updateProgress = () => {
        progressDots.forEach((dot, index) => {
            if (index <= stepIndex && stepIndex < 3) {
                dot.classList.add('is-active');
            } else if (stepIndex >= 3) {
                dot.classList.add('is-active');
            } else {
                dot.classList.remove('is-active');
            }
        });
    };

    const isStepComplete = (index) => {
        if (index === 0) {
            return !!answers.project;
        }
        if (index === 1) {
            return !!answers.budget;
        }
        if (index === 2) {
            return !!answers.audience;
        }
        return true;
    };

    const updateFooter = () => {
        if (!backBtn || !nextBtn) {
            return;
        }
        if (stepIndex >= 3) {
            backBtn.textContent = 'تعديل';
            nextBtn.textContent = 'اختيار جديد';
            backBtn.disabled = false;
            nextBtn.disabled = false;
            return;
        }
        backBtn.textContent = 'رجوع';
        nextBtn.textContent = stepIndex === 2 ? 'اعرض الاقتراح' : 'التالي';
        backBtn.disabled = stepIndex === 0;
        nextBtn.disabled = !isStepComplete(stepIndex);
    };

    const showStep = (index) => {
        stepIndex = index;
        panels.forEach((panel, idx) => {
            panel.hidden = idx !== stepIndex;
        });
        updateProgress();
        updateFooter();
    };

    const buildStoreUrlFromAnswers = () => {
        try {
            const target = new URL(storeUrl, window.location.origin);
            if (answers.project && answers.project !== 'any' && categoryValues.has(answers.project)) {
                target.searchParams.set('category', answers.project);
            }
            if (answers.budget) {
                if (answers.budget.min !== null && answers.budget.min !== undefined) {
                    target.searchParams.set('min_price', answers.budget.min);
                }
                if (answers.budget.max !== null && answers.budget.max !== undefined) {
                    target.searchParams.set('max_price', answers.budget.max);
                }
            }
            return target.toString();
        } catch (error) {
            return storeUrl;
        }
    };

    const getItemText = (item) => {
        return `${item.categoryLabel || ''} ${item.name || ''} ${item.description || ''}`.toLowerCase();
    };

    const countKeywordMatches = (text, keywords) => {
        if (!keywords || !keywords.length) {
            return 0;
        }
        let matches = 0;
        keywords.forEach((keyword) => {
            if (text.includes(keyword.toLowerCase())) {
                matches += 1;
            }
        });
        return matches;
    };

    const scoreService = (item, targetPrice, maxPrice) => {
        let score = 0;
        if (item.inStock) {
            score += 1.5;
        }
        if (item.featured) {
            score += 1.2;
        }
        if (item.discount > 0) {
            score += 0.6;
        }
        if (targetPrice) {
            const distance = Math.abs(item.price - targetPrice);
            const closeness = 1 - Math.min(distance / Math.max(targetPrice, 1), 1);
            score += closeness * 4;
        }
        const text = getItemText(item);
        if (answers.project && answers.project !== 'any' && !categoryValues.has(answers.project)) {
            score += countKeywordMatches(text, projectKeywords[answers.project] || []) * 3;
        }
        if (answers.audience) {
            score += countKeywordMatches(text, audienceKeywords[answers.audience] || []) * 3;
            if (answers.audience === 'simple' && maxPrice) {
                score += ((maxPrice - item.price) / maxPrice) * 2;
            }
        }
        return score;
    };

    const recommendService = () => {
        if (!catalog.length) {
            return null;
        }
        let filtered = catalog;
        if (answers.project && answers.project !== 'any' && categoryValues.has(answers.project)) {
            filtered = filtered.filter((item) => item.category === answers.project);
        } else if (answers.project && answers.project !== 'any') {
            const projectTextKeywords = projectKeywords[answers.project] || [];
            if (projectTextKeywords.length) {
                const projectMatches = filtered.filter((item) => {
                    const text = getItemText(item);
                    return countKeywordMatches(text, projectTextKeywords) > 0;
                });
                if (projectMatches.length) {
                    filtered = projectMatches;
                }
            }
        }
        if (answers.budget) {
            const withinBudget = filtered.filter((item) => {
                if (answers.budget.max === null) {
                    return item.price >= answers.budget.min;
                }
                return item.price >= answers.budget.min && item.price <= answers.budget.max;
            });
            if (withinBudget.length) {
                filtered = withinBudget;
            }
        }
        if (answers.audience) {
            const audienceTextKeywords = audienceKeywords[answers.audience] || [];
            if (audienceTextKeywords.length) {
                const audienceMatches = filtered.filter((item) => {
                    const text = getItemText(item);
                    return countKeywordMatches(text, audienceTextKeywords) > 0;
                });
                if (audienceMatches.length) {
                    filtered = audienceMatches;
                }
            }
        }
        let available = filtered.filter((item) => item.inStock);
        if (!available.length) {
            available = filtered;
        }
        if (!available.length) {
            return null;
        }
        const maxPrice = Math.max(...available.map((item) => item.price), 1);
        let targetPrice = null;
        if (answers.budget) {
            if (answers.budget.max !== null && answers.budget.max !== undefined) {
                targetPrice = (answers.budget.min + answers.budget.max) / 2;
            } else {
                targetPrice = answers.budget.min * 1.1;
            }
        }
        let best = available[0];
        let bestScore = scoreService(best, targetPrice, maxPrice);
        available.forEach((item) => {
            const score = scoreService(item, targetPrice, maxPrice);
            if (score > bestScore) {
                best = item;
                bestScore = score;
            }
        });
        return best;
    };

    const highlightRecommended = (item) => {
        if (!item || !item.id) {
            return;
        }
        const card = document.querySelector(`.product-card[data-id="${item.id}"]`);
        if (card) {
            card.classList.add('is-recommended');
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    };

    const renderResult = (item) => {
        if (!resultEl) {
            return;
        }
        resultEl.innerHTML = '';
        if (!item) {
            const note = document.createElement('p');
            note.className = 'choose-helper-note';
            note.textContent = 'لم نجد خدمة مطابقة بالكامل. يمكنك مشاهدة المتجر للحصول على أفضل الاقتراحات.';
            resultEl.appendChild(note);
            if (resultLink) {
                resultLink.textContent = 'اذهب للمتجر';
                resultLink.setAttribute('href', buildStoreUrlFromAnswers());
            }
            if (seeAllLink) {
                seeAllLink.setAttribute('href', storeUrl);
            }
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'choose-helper-card';

        const media = document.createElement('div');
        media.className = 'choose-helper-media';

        if (item.image) {
            const img = document.createElement('img');
            img.src = item.image;
            img.alt = item.name;
            media.appendChild(img);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'choose-helper-placeholder';
            placeholder.textContent = 'خدمة';
            media.appendChild(placeholder);
        }

        const info = document.createElement('div');
        const category = document.createElement('span');
        category.className = 'choose-helper-category';
        category.textContent = item.categoryLabel || item.category || 'خدمة';

        const title = document.createElement('h4');
        title.textContent = item.name;

        const desc = document.createElement('p');
        desc.textContent = item.description || 'اختيار مناسب حسب إجاباتك.';

        const price = document.createElement('div');
        price.className = 'choose-helper-price';
        const currency = getCurrencyLabel();
        price.textContent = item.price ? `${item.price} ${currency}` : currency;

        info.appendChild(category);
        info.appendChild(title);
        info.appendChild(desc);
        info.appendChild(price);

        wrapper.appendChild(media);
        wrapper.appendChild(info);
        resultEl.appendChild(wrapper);

        if (resultLink) {
            resultLink.textContent = 'شاهد الخدمة';
            resultLink.setAttribute('href', item.url || '#');
        }
        if (seeAllLink) {
            seeAllLink.setAttribute('href', storeUrl);
        }
        highlightRecommended(item);
    };

    const openModal = ({ preserveState = false } = {}) => {
        catalog = loadCatalog();
        if (!preserveState) {
            initAnswers();
            stepIndex = 0;
        }
        renderQuestions();
        showStep(stepIndex);
        modal.classList.add('show');
        modal.setAttribute('aria-hidden', 'false');
        if (document.body) {
            document.body.classList.add('choose-helper-open');
        }
    };

    const closeModal = () => {
        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
        if (document.body) {
            document.body.classList.remove('choose-helper-open');
        }
    };

    const savePending = () => {
        writeStorage(storageKeys.pending, {
            answers,
            ts: Date.now(),
        });
    };

    const loadPending = () => {
        const payload = readStorage(storageKeys.pending);
        if (!payload || !payload.answers) {
            return null;
        }
        const ageMs = Date.now() - (payload.ts || 0);
        if (ageMs > 24 * 60 * 60 * 1000) {
            return null;
        }
        return payload.answers;
    };

    const clearPending = () => {
        try {
            window.localStorage.removeItem(storageKeys.pending);
        } catch (error) {
            return;
        }
    };

    openButtons.forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            openModal();
        });
    });

    closeButtons.forEach((button) => {
        button.addEventListener('click', closeModal);
    });

    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && modal.classList.contains('show')) {
            closeModal();
        }
    });

    modal.addEventListener('click', (event) => {
        const option = event.target.closest('.choose-helper-option');
        if (!option) {
            return;
        }
        const question = option.dataset.question;
        if (!question) {
            return;
        }
        const container = questionContainers[question];
        if (container) {
            container.querySelectorAll('.choose-helper-option').forEach((btn) => {
                btn.classList.remove('is-selected');
            });
        }
        option.classList.add('is-selected');
        if (question === 'project') {
            answers.project = option.dataset.value || 'any';
        } else if (question === 'budget') {
            const minValue = option.dataset.min ? parseNumber(option.dataset.min) : 0;
            const maxValue = option.dataset.max ? parseNumber(option.dataset.max) : null;
            answers.budget = {
                key: option.dataset.value,
                min: minValue,
                max: maxValue,
            };
        } else if (question === 'audience') {
            answers.audience = option.dataset.value || null;
        }
        updateFooter();
    });

    if (backBtn) {
        backBtn.addEventListener('click', () => {
            if (stepIndex >= 3) {
                showStep(2);
                return;
            }
            if (stepIndex > 0) {
                showStep(stepIndex - 1);
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (stepIndex >= 3) {
                openModal();
                return;
            }
            if (!isStepComplete(stepIndex)) {
                return;
            }
            if (stepIndex < 2) {
                showStep(stepIndex + 1);
                return;
            }
            const recommendation = recommendService();
            renderResult(recommendation);
            if (!catalog.length) {
                savePending();
            }
            showStep(3);
        });
    }

    const pendingAnswers = loadPending();
    if (pendingAnswers) {
        initAnswers();
        answers = {
            project: pendingAnswers.project || 'any',
            budget: pendingAnswers.budget || null,
            audience: pendingAnswers.audience || null,
        };
        catalog = loadCatalog();
        if (catalog.length) {
            stepIndex = 3;
            renderQuestions();
            renderResult(recommendService());
            openModal({ preserveState: true });
            clearPending();
        }
    }
})();
