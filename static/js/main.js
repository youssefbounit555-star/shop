// =========================
// DOM Elements
// =========================
const menuToggle = document.getElementById('menuToggle');
const mobileMenu = document.getElementById('mobileMenu');
const searchBtn = document.getElementById('searchBtn');
const searchBar = document.getElementById('searchBar');
const closeSearch = document.getElementById('closeSearch');
const cartBtn = document.getElementById('cartBtn');
const userBtn = document.getElementById('userBtn');
const cartModal = document.getElementById('cartModal');
const userModal = document.getElementById('userModal');
const successAlert = document.getElementById('successAlert');
const learnMoreBtn = document.getElementById('learnMoreBtn');
const addToCartButtons = document.querySelectorAll('.btn-add-cart');
const closeModalButtons = document.querySelectorAll('.close-modal');
const cartBadge = cartBtn.querySelector('.badge');

let cartCount = 0;

// =========================
// MOBILE MENU
// =========================
menuToggle.addEventListener('click', () => {
    menuToggle.classList.toggle('active');
    mobileMenu.classList.toggle('active');
});

// Close menu when clicking on a link
document.querySelectorAll('.mobile-menu a').forEach(link => {
    link.addEventListener('click', () => {
        menuToggle.classList.remove('active');
        mobileMenu.classList.remove('active');
    });
});

// =========================
// SEARCH BAR
// =========================
searchBtn.addEventListener('click', () => {
    searchBar.classList.add('active');
    searchBar.querySelector('input').focus();
});

closeSearch.addEventListener('click', () => {
    searchBar.classList.remove('active');
});

// Close search bar when pressing Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        searchBar.classList.remove('active');
    }
});

// =========================
// CART MODAL
// =========================
cartBtn.addEventListener('click', () => {
    cartModal.classList.add('active');
});

// =========================
// USER MODAL
// =========================
userBtn.addEventListener('click', () => {
    userModal.classList.add('active');
});

// =========================
// CLOSE MODALS
// =========================
closeModalButtons.forEach(button => {
    button.addEventListener('click', () => {
        cartModal.classList.remove('active');
        userModal.classList.remove('active');
    });
});

// Close modals when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === cartModal) {
        cartModal.classList.remove('active');
    }
    if (e.target === userModal) {
        userModal.classList.remove('active');
    }
});

// =========================
// ADD TO CART
// =========================
addToCartButtons.forEach((button, index) => {
    button.addEventListener('click', (e) => {
        e.stopPropagation();
        
        const productCard = button.closest('.product-card');
        const productName = productCard.querySelector('.product-name').textContent;
        const productPrice = productCard.querySelector('.product-price').textContent;
        
        // Increment cart count
        cartCount++;
        cartBadge.textContent = cartCount;
        
        // Show success alert
        showAlert(`${productName} added to cart!`);
        
        // Add animation to button
        button.style.transform = 'scale(0.9)';
        setTimeout(() => {
            button.style.transform = 'scale(1)';
        }, 200);
        
        // Add item to cart modal
        updateCartModal(productName, productPrice);
    });
});

// Update cart modal with new items
function updateCartModal(productName, productPrice) {
    const cartModalBody = cartModal.querySelector('.modal-body');
    
    // Check if it's the first item
    if (cartCount === 1) {
        cartModalBody.innerHTML = '';
    }
    
    const emptyMsg = cartModalBody.querySelector('.empty-cart-msg');
    if (emptyMsg) {
        emptyMsg.remove();
    }
    
    // Create cart item element
    const cartItem = document.createElement('div');
    cartItem.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        border-bottom: 1px solid #e5e7eb;
        font-size: 0.95rem;
    `;
    cartItem.innerHTML = `
        <span>${productName}</span>
        <span style="color: #6366f1; font-weight: 600;">${productPrice}</span>
    `;
    
    cartModalBody.appendChild(cartItem);
}

// =========================
// ALERTS
// =========================
function showAlert(message, duration = 3000) {
    successAlert.querySelector('span').textContent = message;
    successAlert.classList.add('show');
    
    setTimeout(() => {
        successAlert.classList.remove('show');
    }, duration);
}

// =========================
// LEARN MORE BUTTON
// =========================
learnMoreBtn.addEventListener('click', () => {
    // Scroll to featured section
    const featuredSection = document.querySelector('.featured-section');
    featuredSection.scrollIntoView({ behavior: 'smooth' });
});

// =========================
// PRODUCT CARD INTERACTIONS
// =========================

// Heart (Wishlist) buttons
document.querySelectorAll('.icon-btn-sm').forEach(button => {
    button.addEventListener('click', (e) => {
        e.stopPropagation();
        
        if (button.querySelector('.fa-heart')) {
            const icon = button.querySelector('i');
            icon.classList.toggle('fas');
            icon.classList.toggle('far');
            
            if (icon.classList.contains('fas')) {
                showAlert('Added to wishlist!', 2000);
            } else {
                showAlert('Removed from wishlist', 2000);
            }
        }
        
        // Quick view functionality (placeholder)
        if (button.querySelector('.fa-eye')) {
            showAlert('Opening product details...', 2000);
        }
    });
});

// =========================
// SMOOTH SCROLL ON LINKS
// =========================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// =========================
// NEWSLETTER FORM
// =========================
const newsletterForm = document.querySelector('.newsletter-form');
if (newsletterForm) {
    newsletterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = newsletterForm.querySelector('input').value;
        showAlert(`Thank you for subscribing with ${email}!`, 3000);
        newsletterForm.querySelector('input').value = '';
    });
}

// =========================
// SCROLL ANIMATIONS
// =========================
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '0';
            entry.target.style.transform = 'translateY(30px)';
            
            setTimeout(() => {
                entry.target.style.transition = 'all 0.6s ease';
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }, 100);
            
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe product cards
document.querySelectorAll('.product-card').forEach(card => {
    observer.observe(card);
});

// Observe category cards
document.querySelectorAll('.category-card').forEach(card => {
    observer.observe(card);
});

// Observe feature cards
document.querySelectorAll('.feature-card').forEach(card => {
    observer.observe(card);
});

// =========================
// HEADER ACTIVE STATE
// =========================
document.querySelectorAll('.nav-menu a').forEach(link => {
    link.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-menu a').forEach(l => {
            l.classList.remove('active');
        });
        link.classList.add('active');
    });
});

// Set active link on page load
window.addEventListener('load', () => {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-menu a').forEach(link => {
        if (link.getAttribute('href').includes(currentPage)) {
            link.classList.add('active');
        }
    });
});

// =========================
// HOVER EFFECTS ON BUTTONS
// =========================
document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('mouseenter', function() {
        this.style.animation = 'none';
        setTimeout(() => {
            this.style.animation = '';
        }, 10);
    });
});

// =========================
// IMAGE LAZY LOADING SIMULATION
// =========================
// Note: In a real scenario, you would use actual images with lazy loading
// This is a placeholder for the colorful gradient backgrounds

// =========================
// UTILITY FUNCTIONS
// =========================

// Format currency (placeholder)
function formatCurrency(amount) {
    return `$${amount.toFixed(2)}`;
}

// Format date
function formatDate(date) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// =========================
// INITIALIZATION
// =========================
document.addEventListener('DOMContentLoaded', () => {
    // Add smooth animations on load
    document.body.style.opacity = '1';
    
    // Initialize cart
    if (cartCount === 0) {
        cartBadge.textContent = '0';
    }
    
    console.log('ElegantShop - E-commerce website loaded successfully!');
});

// =========================
// KEYBOARD SHORTCUTS
// =========================
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchBar.classList.add('active');
        searchBar.querySelector('input').focus();
    }
    
    // Ctrl/Cmd + / for help (in future)
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        // Show help modal (to be implemented)
    }
});

// =========================
// PERFORMANCE OPTIMIZATION
// =========================
// Debounce function for resize events
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Handle window resize
const handleResize = debounce(() => {
    if (window.innerWidth > 768) {
        menuToggle.classList.remove('active');
        mobileMenu.classList.remove('active');
    }
}, 250);

window.addEventListener('resize', handleResize);

// =========================
// CURRENCY AND LOCALIZATION
// =========================
// Placeholder for future localization features
const userLocale = navigator.language || navigator.userLanguage;
console.log('User locale:', userLocale);

// =========================
// ANALYTICS PLACEHOLDER
// =========================
// Placeholder for tracking
function trackEvent(eventName, eventData = {}) {
    console.log(`Event tracked: ${eventName}`, eventData);
    // In a real app, this would send data to an analytics service
}

// Track page views
trackEvent('page_view', {
    page: window.location.pathname,
    timestamp: new Date()
});

// =========================
// STORE PAGE - PRICE SLIDER
// =========================

const priceSlider = document.querySelector('.price-slider');
const priceValue = document.getElementById('priceValue');

if (priceSlider && priceValue) {
    priceSlider.addEventListener('input', (e) => {
        const value = e.target.value;
        priceValue.textContent = '$' + value;
        trackEvent('filter_price', { price: value });
    });
}

// =========================
// STORE PAGE - PAGINATION
// =========================

const paginationButtons = document.querySelectorAll('.pagination-btn');

paginationButtons.forEach((button, index) => {
    button.addEventListener('click', () => {
        paginationButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        trackEvent('pagination_click', { page: button.textContent });
    });
});

// =========================
// STORE PAGE - SORT FUNCTIONALITY
// =========================

const sortSelect = document.getElementById('sortSelect');

if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
        trackEvent('sort_products', { sortBy: e.target.value });
        console.log('Products sorted by:', e.target.value);
    });
}

// =========================
// STORE PAGE - FILTER CHECKBOXES
// =========================

const filterCheckboxes = document.querySelectorAll('.filter-checkbox input');

filterCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
        const filterName = e.target.closest('.filter-group').querySelector('h4').textContent;
        const isChecked = e.target.checked;
        trackEvent('filter_applied', { 
            filter: filterName, 
            checked: isChecked 
        });
    });
});

// =========================
// APPLY FILTERS BUTTON
// =========================

const applyFiltersBtn = document.querySelector('.filters-sidebar .btn-primary');

if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener('click', () => {
        showAlert('Filters applied! Showing relevant products.', 2000);
        trackEvent('apply_filters', { timestamp: new Date() });
    });
}

// =========================
// CLEAR FILTERS BUTTON
// =========================

const clearFiltersBtn = document.querySelectorAll('.filters-sidebar .btn-secondary')[0];

if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
        filterCheckboxes.forEach(checkbox => {
            if (!checkbox.closest('.filter-group').querySelector('h4').textContent.includes('All')) {
                checkbox.checked = false;
            }
        });
        if (priceSlider) {
            priceSlider.value = 500;
            priceValue.textContent = '$500';
        }
        showAlert('Filters cleared!', 2000);
        trackEvent('clear_filters', { timestamp: new Date() });
    });
}
