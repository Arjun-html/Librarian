// Handle book card expansion
document.querySelectorAll('.book-card').forEach(card => {
    card.addEventListener('click', function(e) {
        this.classList.toggle('expanded');
    });
});

// Allow clicking on header to expand as well
document.querySelectorAll('.book-header').forEach(header => {
    header.style.cursor = 'pointer';
});
