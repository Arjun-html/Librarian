// Arriving via a page-flip? Skip the entrance fade so it doesn't blink.
try {
  if (Date.now() - (parseInt(sessionStorage.getItem('arjun_flip_at'), 10) || 0) < 4000)
    document.documentElement.classList.add('flip-arriving');
} catch (e) {}
