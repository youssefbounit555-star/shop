/* ===============================================
   DASHBOARD JAVASCRIPT - Interactive Features
   =============================================== */

document.addEventListener('DOMContentLoaded', function() {
    // Sidebar Toggle
    initSidebarToggle();
    
    // User Dropdown
    initUserDropdown();
    
    // Animate Counters
    animateCounters();
    
    // Message Textarea Auto-expand
    initMessageTextarea();
    
    // Conversation Search
    initConversationSearch();
});

/**
 * Sidebar Toggle for Mobile
 */
function initSidebarToggle() {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('dashboardSidebar');
    
    if (!toggle || !sidebar) return;
    
    toggle.addEventListener('click', function() {
        sidebar.classList.toggle('active');
    });
    
    // Close sidebar when clicking on a link
    document.querySelectorAll('.dashboard-sidebar a').forEach(link => {
        link.addEventListener('click', function() {
            sidebar.classList.remove('active');
        });
    });
    
    // Close sidebar when clicking elsewhere
    document.addEventListener('click', function(event) {
        if (!sidebar.contains(event.target) && !toggle.contains(event.target)) {
            sidebar.classList.remove('active');
        }
    });
}

/**
 * User Dropdown Menu
 */
function initUserDropdown() {
    const userBtn = document.getElementById('userDropdownBtn');
    const dropdown = document.getElementById('userDropdown');
    
    if (!userBtn || !dropdown) return;
    
    userBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    });
    
    document.addEventListener('click', function(e) {
        if (!userBtn.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

/**
 * Animate Counter Numbers
 */
function animateCounters() {
    const counters = document.querySelectorAll('.counter');
    
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const start = 0;
        const duration = 2000;
        const increment = target / (duration / 50);
        
        let current = start;
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                counter.textContent = target;
                clearInterval(timer);
            } else {
                counter.textContent = Math.floor(current);
            }
        }, 50);
    });
}

/**
 * Message Textarea Auto-expand
 */
function initMessageTextarea() {
    const textarea = document.querySelector('.message-textarea');
    
    if (!textarea) return;
    
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight > 120 ? 120 : this.scrollHeight) + 'px';
    });
}

/**
 * Conversation Search
 */
function initConversationSearch() {
    const searchInput = document.querySelector('.conversations-search');
    
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.conversation-item').forEach(item => {
            const name = item.querySelector('.conversation-name').textContent.toLowerCase();
            item.style.display = name.includes(query) ? 'flex' : 'none';
        });
    });
}

/**
 * Get CSRF Token for AJAX requests
 */
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

/**
 * Auto-scroll messages to bottom
 */
function scrollToBottom() {
    const messagesArea = document.getElementById('messagesArea');
    if (messagesArea) {
        setTimeout(() => {
            messagesArea.scrollTop = messagesArea.scrollHeight;
        }, 100);
    }
}

// Initialize scroll on page load
if (document.getElementById('messagesArea')) {
    window.addEventListener('load', scrollToBottom);
}
