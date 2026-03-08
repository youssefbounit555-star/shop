// =========================
// FAQ ACCORDION FUNCTIONALITY
// =========================

document.addEventListener('DOMContentLoaded', () => {
    // Get all accordion headers
    const accordionHeaders = document.querySelectorAll('.accordion-header');
    
    // Add click event listeners to each header
    accordionHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const accordionItem = header.parentElement;
            const isActive = accordionItem.classList.contains('active');
            
            // Close all accordion items
            document.querySelectorAll('.accordion-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Open clicked accordion item if it wasn't active
            if (!isActive) {
                accordionItem.classList.add('active');
            }
        });
    });
});

// =========================
// FAQ SEARCH FUNCTIONALITY
// =========================

const faqSearch = document.getElementById('faqSearch');

if (faqSearch) {
    faqSearch.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const accordionItems = document.querySelectorAll('.accordion-item');
        
        accordionItems.forEach(item => {
            const question = item.querySelector('.accordion-header span').textContent.toLowerCase();
            const answer = item.querySelector('.accordion-content p').textContent.toLowerCase();
            
            if (question.includes(searchTerm) || answer.includes(searchTerm)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
        
        // Show a message if no results found
        const visibleItems = Array.from(accordionItems).filter(item => item.style.display !== 'none');
        if (visibleItems.length === 0 && searchTerm.length > 0) {
            console.log('No FAQs found matching your search');
        }
    });
}

// =========================
// SMOOTH SCROLL TO ACCORDIONS
// =========================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target && target.classList.contains('accordion-item')) {
            target.classList.add('active');
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});
