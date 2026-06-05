// Mobile navigation: toggle the hamburger dropdown.
// Delegated so it works no matter when the DOM finishes loading, and
// alongside page-transition.js (which handles the actual link navigation).
document.addEventListener('click', function (e) {
    const burger = e.target.closest('.nav-hamburger');
    if (burger) {
        const nav = burger.closest('nav');
        if (nav) nav.classList.toggle('nav-open');
        return;
    }
    // Close the menu after a nav link is chosen.
    const link = e.target.closest('.nav-links a');
    if (link) {
        const nav = link.closest('nav');
        if (nav) nav.classList.remove('nav-open');
    }
});
