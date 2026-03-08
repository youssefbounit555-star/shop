/* ===============================================
   COMPONENTS JS - All Components Interactivity
   =============================================== */

document.addEventListener('DOMContentLoaded', function() {

    // ===================== ALERTS =====================
    const alertCloseButtons = document.querySelectorAll('.alert-close');
    alertCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const alert = this.closest('.alert');
            alert.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                alert.remove();
            }, 300);
        });
    });

    // ===================== FORMS =====================
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formInputs = this.querySelectorAll('input');
            let isValid = true;

            formInputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.style.borderColor = '#ef4444';
                } else {
                    input.style.borderColor = '#10b981';
                    input.style.borderWidth = '2px';
                }
            });

            if (isValid) {
                showAlert('success', 'تم تسجيل الدخول بنجاح!');
                setTimeout(() => {
                    this.reset();
                    formInputs.forEach(input => {
                        input.style.borderColor = '#e5e7eb';
                    });
                }, 1500);
            } else {
                showAlert('error', 'الرجاء ملء جميع الحقول المطلوبة');
            }
        });
    }

    // Form inputs focus effects
    const formInputs = document.querySelectorAll('.form-control');
    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.style.transform = 'scale(1.02)';
        });

        input.addEventListener('blur', function() {
            this.style.transform = 'scale(1)';
        });
    });

    // ===================== BUTTONS =====================
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            if (!this.classList.contains('is-loading') && !this.disabled) {
                // Add click animation
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = 'scale(1)';
                }, 100);
            }
        });
    });

    // ===================== NOTIFICATION DROPDOWN =====================
    const notificationBtn = document.getElementById('notificationBtn');
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            showAlert('info', 'عدد الإشعارات الجديدة: 3');
        });
    }

    // ===================== DROPDOWN MENU =====================
    const userProfileBtn = document.querySelector('.user-profile-btn');
    const dropdownMenu = document.querySelector('.dropdown-menu');
    
    if (userProfileBtn && dropdownMenu) {
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.user-profile-dropdown')) {
                dropdownMenu.style.opacity = '0';
                dropdownMenu.style.visibility = 'hidden';
            }
        });
    }

    // ===================== MODALS =====================
    const confirmModalBtn = document.getElementById('confirmModalBtn');
    const infoModalBtn = document.getElementById('infoModalBtn');
    const confirmModal = document.getElementById('confirmModal');
    const infoModal = document.getElementById('infoModal');
    const confirmCancel = document.getElementById('confirmCancel');
    const infoClose = document.getElementById('infoClose');

    if (confirmModalBtn && confirmModal) {
        confirmModalBtn.addEventListener('click', function() {
            confirmModal.classList.add('show');
        });

        const confirmClose = confirmModal.querySelector('.modal-close');
        if (confirmClose) {
            confirmClose.addEventListener('click', function() {
                confirmModal.classList.remove('show');
            });
        }

        if (confirmCancel) {
            confirmCancel.addEventListener('click', function() {
                confirmModal.classList.remove('show');
            });
        }

        confirmModal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('show');
            }
        });
    }

    if (infoModalBtn && infoModal) {
        infoModalBtn.addEventListener('click', function() {
            infoModal.classList.add('show');
        });

        const infoCloseBtn = infoModal.querySelector('.modal-close');
        if (infoCloseBtn) {
            infoCloseBtn.addEventListener('click', function() {
                infoModal.classList.remove('show');
            });
        }

        if (infoClose) {
            infoClose.addEventListener('click', function() {
                infoModal.classList.remove('show');
            });
        }

        infoModal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('show');
            }
        });
    }

    // ===================== KEYBOARD SHORTCUTS =====================
    document.addEventListener('keydown', function(e) {
        // Close modals with Escape
        if (e.key === 'Escape') {
            if (confirmModal) confirmModal.classList.remove('show');
            if (infoModal) infoModal.classList.remove('show');
        }
    });

    // ===================== NOTIFICATION CLOSE =====================
    const notificationCloseButtons = document.querySelectorAll('.notification-close');
    notificationCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const notification = this.closest('.notification-item');
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
    });

    // ===================== SIDEBAR NAVIGATION =====================
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            // Remove active class from all links
            navLinks.forEach(l => l.classList.remove('active'));
            // Add active class to clicked link
            this.classList.add('active');
            showAlert('info', 'تم الانتقال إلى: ' + this.textContent.trim());
        });
    });

    // ===================== ADMIN LOGOUT =====================
    const logoutBtn = document.querySelector('.admin-logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('هل أنت متأكد من رغبتك في تسجيل الخروج؟')) {
                showAlert('success', 'تم تسجيل الخروج بنجاح');
            }
        });
    }

    // ===================== TOGGLE SWITCHES =====================
    const toggles = document.querySelectorAll('.toggle input');
    toggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const label = this.closest('.toggle').nextElementSibling;
            if (label) {
                const status = this.checked ? 'مفعل' : 'معطل';
                showAlert('info', 'تم التغيير إلى: ' + status);
            }
        });
    });

    // ===================== HELPER FUNCTIONS =====================

    // Show Alert Function
    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        
        let icon = '';
        switch(type) {
            case 'success':
                icon = '<i class="fas fa-check-circle"></i>';
                break;
            case 'error':
                icon = '<i class="fas fa-exclamation-circle"></i>';
                break;
            case 'warning':
                icon = '<i class="fas fa-exclamation-triangle"></i>';
                break;
            case 'info':
                icon = '<i class="fas fa-info-circle"></i>';
                break;
        }

        alertDiv.innerHTML = `
            ${icon}
            <span>${message}</span>
            <button class="alert-close">&times;</button>
        `;

        // Insert at the top of the page
        const container = document.querySelector('.admin-main') || document.body;
        container.insertBefore(alertDiv, container.firstChild);

        // Auto remove after 4 seconds
        setTimeout(() => {
            alertDiv.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                alertDiv.remove();
            }, 300);
        }, 4000);

        // Close button functionality
        const closeBtn = alertDiv.querySelector('.alert-close');
        closeBtn.addEventListener('click', function() {
            alertDiv.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                alertDiv.remove();
            }, 300);
        });
    }

    // ===================== ANIMATIONS =====================
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideOut {
            0% {
                opacity: 1;
                transform: translateX(0);
            }
            100% {
                opacity: 0;
                transform: translateX(100px);
            }
        }
    `;
    document.head.appendChild(style);

    // ===================== SMOOTH TRANSITIONS =====================
    const componentCards = document.querySelectorAll('.component-card');
    componentCards.forEach((card, index) => {
        card.style.animation = `fadeInUp 0.5s ease ${index * 0.05}s backwards`;
    });

    const componentsSection = document.querySelectorAll('.components-section');
    componentsSection.forEach((section, index) => {
        section.style.animation = `fadeInUp 0.5s ease ${index * 0.1}s backwards`;
    });

    // Add fade-in animation
    const animationStyle = document.createElement('style');
    animationStyle.textContent = `
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(animationStyle);

    // ===================== RIPPLE EFFECT =====================
    function addRippleEffect(element) {
        element.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            ripple.style.position = 'absolute';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.style.width = '10px';
            ripple.style.height = '10px';
            ripple.style.background = 'rgba(255, 255, 255, 0.5)';
            ripple.style.borderRadius = '50%';
            ripple.style.animation = 'ripple 0.6s ease-out';
            ripple.style.pointerEvents = 'none';

            this.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    }

    // Add ripple effect to buttons
    const allButtons = document.querySelectorAll('button');
    allButtons.forEach(button => {
        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        addRippleEffect(button);
    });

    // ===================== TOOLTIP FUNCTIONALITY =====================
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            // Already handled by CSS
        });
    });

    // ===================== TABLE INTERACTIONS =====================
    const tableRows = document.querySelectorAll('.data-table tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function() {
            tableRows.forEach(r => r.style.background = '');
            this.style.background = '#iff6ff';
        });
    });

    // ===================== LOADING SIMULATION =====================
    const isLoadingButtons = document.querySelectorAll('.is-loading');
    isLoadingButtons.forEach(button => {
        const originalText = button.textContent;
        button.addEventListener('click', function() {
            if (!button.classList.contains('loading-active')) {
                button.classList.add('loading-active');
                button.disabled = true;
                
                setTimeout(() => {
                    button.classList.remove('loading-active');
                    button.disabled = false;
                    showAlert('success', 'اكتملت العملية بنجاح');
                }, 2000);
            }
        });
    });

    console.log('✅ جميع المكونات تم تحميلها بنجاح');

});

// ===================== OBSERVE ANIMATION =====================
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animation = 'fadeInUp 0.6s ease forwards';
        }
    });
}, observerOptions);

document.querySelectorAll('.component-card').forEach(card => {
    observer.observe(card);
});
