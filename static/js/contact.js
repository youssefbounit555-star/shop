// =========================
// CONTACT FORM HANDLING
// =========================

document.addEventListener('DOMContentLoaded', () => {
    const contactForm = document.getElementById('contactForm');
    const messages = getContactMessages(contactForm);

    if (contactForm) {
        // Add form validation and submission
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            // Get form values
            const fullName = document.getElementById('fullName').value.trim();
            const email = document.getElementById('email').value.trim();
            const phone = document.getElementById('phone').value.trim();
            const subject = document.getElementById('subject').value;
            const message = document.getElementById('message').value.trim();
            const subscribe = document.getElementById('subscribe').checked;
            
            // Basic validation
            if (!fullName || !email || !subject || !message) {
                showAlert(messages.required, 'error');
                return;
            }
            
            // Email validation
            if (!isValidEmail(email)) {
                showAlert(messages.invalidEmail, 'error');
                return;
            }
            
            // Phone validation (if provided)
            if (phone && !isValidPhone(phone)) {
                showAlert(messages.invalidPhone, 'error');
                return;
            }
            
            // Simulate form submission
            console.log('Form Data:', {
                fullName,
                email,
                phone,
                subject,
                message,
                subscribe,
                timestamp: new Date()
            });
            
            // Show success message
            showAlert(messages.success, 'success');
            
            // Reset form
            contactForm.reset();
        });
    }
});

// =========================
// EMAIL VALIDATION
// =========================

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// =========================
// PHONE VALIDATION
// =========================

function isValidPhone(phone) {
    const phoneRegex = /^[\d\s\-\+\(\)]+$/;
    return phoneRegex.test(phone) && phone.replace(/\D/g, '').length >= 10;
}

// =========================
// FORM INPUT FORMATTING
// =========================

const phoneInput = document.getElementById('phone');
if (phoneInput) {
    phoneInput.addEventListener('input', (e) => {
        let value = e.target.value.replace(/\D/g, '');
        
        if (value.length > 0) {
            if (value.length <= 3) {
                e.target.value = value;
            } else if (value.length <= 6) {
                e.target.value = value.slice(0, 3) + '-' + value.slice(3);
            } else if (value.length <= 10) {
                e.target.value = value.slice(0, 3) + '-' + value.slice(3, 6) + '-' + value.slice(6);
            } else {
                e.target.value = value.slice(0, 3) + '-' + value.slice(3, 6) + '-' + value.slice(6, 10);
            }
        }
    });
}

// =========================
// FORM FIELD FOCUS EFFECTS
// =========================

const formInputs = document.querySelectorAll('.contact-form input, .contact-form select, .contact-form textarea');

formInputs.forEach(input => {
    input.addEventListener('focus', function() {
        this.parentElement.style.transform = 'scale(1.02)';
    });
    
    input.addEventListener('blur', function() {
        this.parentElement.style.transform = 'scale(1)';
    });
});

// =========================
// SHOW ALERT
// =========================

function showAlert(message, type = 'success') {
    const alertElement = document.getElementById('successAlert');
    
    if (alertElement) {
        // Update alert message
        alertElement.querySelector('span').textContent = message;
        
        // Update alert styling based on type
        if (type === 'error') {
            alertElement.classList.remove('alert-success');
            alertElement.classList.add('alert-error');
            alertElement.querySelector('i').className = 'fas fa-exclamation-circle';
        } else {
            alertElement.classList.add('alert-success');
            alertElement.classList.remove('alert-error');
            alertElement.querySelector('i').className = 'fas fa-check-circle';
        }
        
        // Show alert
        alertElement.classList.add('show');
        
        // Hide after 3 seconds
        setTimeout(() => {
            alertElement.classList.remove('show');
        }, 3000);
    }
}

// =========================
// CHARACTER COUNTER FOR TEXTAREA
// =========================

const messageTextarea = document.getElementById('message');

if (messageTextarea) {
    // Optional: Add character counter
    messageTextarea.addEventListener('input', (e) => {
        const charCount = e.target.value.length;
        const maxChars = 1000;
        
        // Could display counter if desired
        if (charCount > maxChars) {
            e.target.value = e.target.value.substring(0, maxChars);
        }
    });
}

// =========================
// CATEGORY BUTTONS CLICK HANDLER
// =========================

document.querySelectorAll('.category-box').forEach(box => {
    box.addEventListener('click', () => {
        // Scroll to contact form
        const contactForm = document.getElementById('contactForm');
        if (contactForm) {
            contactForm.scrollIntoView({ behavior: 'smooth' });
            
            // Optional: Pre-fill subject based on clicked category
            const subjectSelect = document.getElementById('subject');

            if (subjectSelect && box.dataset.subject) {
                subjectSelect.value = box.dataset.subject;
            }
        }
    });
});

// =========================
// PREVENT MULTIPLE SUBMISSIONS
// =========================

let isSubmitting = false;

const submitButton = document.querySelector('.contact-form button[type="submit"]');

if (submitButton) {
    const originalHtml = submitButton.innerHTML;
    const messages = getContactMessages(document.getElementById('contactForm'));
    
    submitButton.addEventListener('click', () => {
        if (isSubmitting) {
            return false;
        }
        
        isSubmitting = true;
        submitButton.disabled = true;
        submitButton.textContent = messages.sending;
        
        // Reset after 3 seconds
        setTimeout(() => {
            isSubmitting = false;
            submitButton.disabled = false;
            submitButton.innerHTML = originalHtml;
        }, 3000);
    });
}

// =========================
// ADD ERROR STYLING TO MAIN.CSS
// =========================

const style = document.createElement('style');
style.textContent = `
    .alert-error {
        border-left: 4px solid var(--danger) !important;
    }
    
    .alert-error i {
        color: var(--danger) !important;
    }
    
    .form-group input.error,
    .form-group select.error,
    .form-group textarea.error {
        border-color: var(--danger);
        background-color: var(--light);
    }
`;

document.head.appendChild(style);

function getContactMessages(form) {
    const geoStrings = window.geoStrings || {};
    const data = form ? form.dataset : {};

    return {
        required: data.msgRequired || geoStrings.contact_error_required || 'Please fill in all required fields',
        invalidEmail: data.msgInvalidEmail || geoStrings.contact_error_email || 'Please enter a valid email address',
        invalidPhone: data.msgInvalidPhone || geoStrings.contact_error_phone || 'Please enter a valid phone number',
        success: data.msgSuccess || geoStrings.contact_success_message || 'Message sent successfully! We\'ll get back to you soon.',
        sending: data.msgSending || geoStrings.contact_sending || 'Sending...',
    };
}
