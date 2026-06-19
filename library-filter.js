/**
 * Client-side search + section/status filter for library.html.
 * Reads data-section / data-status attributes on each .book-tile and
 * shows/hides tiles without any page reload.
 */
(function () {
    'use strict';

    const grid   = document.getElementById('library-grid');
    const search = document.getElementById('lib-search');
    const btns   = document.querySelectorAll('.lib-filter-btn');
    const empty  = document.getElementById('lib-empty');

    if (!grid) return;

    const tiles = Array.from(grid.querySelectorAll('.book-tile'));

    let activeFilter = 'all';
    let searchQuery  = '';
    let searchTimer;

    function normalize(s) {
        return s.toLowerCase().replace(/[^\w\s]/g, ' ').replace(/\s+/g, ' ').trim();
    }

    function applyFilters() {
        const q = normalize(searchQuery);
        let visible = 0;

        // Trigger the reveal animation on newly-shown tiles
        grid.classList.add('is-filtering');

        tiles.forEach(function (tile) {
            var section = tile.dataset.section || '';
            var status  = tile.dataset.status  || '';
            var title   = normalize(tile.querySelector('.tile-title')  ? tile.querySelector('.tile-title').textContent  : '');
            var author  = normalize(tile.querySelector('.tile-author') ? tile.querySelector('.tile-author').textContent : '');

            var sectionMatch =
                activeFilter === 'all' ||
                section === activeFilter ||
                (activeFilter === 'reading' && status === 'reading');

            var textMatch = !q || title.indexOf(q) !== -1 || author.indexOf(q) !== -1;

            if (sectionMatch && textMatch) {
                tile.removeAttribute('hidden');
                visible++;
            } else {
                tile.setAttribute('hidden', '');
            }
        });

        // Show/hide empty state
        if (empty) {
            if (visible > 0) {
                empty.setAttribute('hidden', '');
            } else {
                empty.removeAttribute('hidden');
            }
        }

        // Remove animation class after it completes
        setTimeout(function () { grid.classList.remove('is-filtering'); }, 220);
    }

    // Filter button clicks
    btns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            btns.forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            activeFilter = btn.dataset.filter;
            applyFilters();
        });
    });

    // Search input — debounced 150 ms
    if (search) {
        search.addEventListener('input', function () {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(function () {
                searchQuery = search.value;
                applyFilters();
            }, 150);
        });

        // Esc clears the search field
        search.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                search.value = '';
                searchQuery = '';
                applyFilters();
                search.blur();
            }
        });
    }
}());
