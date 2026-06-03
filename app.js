// Handle book card expansion
document.querySelectorAll('.book-card').forEach(card => {
    card.addEventListener('click', function(e) {
        // Don't close if clicking on utterances comment section
        if (e.target.closest('.comments-section') || e.target.closest('iframe')) {
            return;
        }

        this.classList.toggle('expanded');
    });
});

// Allow clicking on header to expand as well
document.querySelectorAll('.book-header').forEach(header => {
    header.style.cursor = 'pointer';
});
