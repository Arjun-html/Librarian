/**
 * Soft newspaper page-turn with REAL page content on the turning sheet.
 *
 * The current viewport is captured with html2canvas, then that bitmap is
 * mapped strip-by-strip onto a single cylindrical curl drawn on a <canvas>.
 * The page therefore keeps its text/headlines as it lifts and rolls away —
 * it does not go blank — and because the shading is a single monotonic curve
 * (no repeated highlight bands) it reads as ONE sheet, not several.
 *
 * The destination page loads in an iframe beneath the canvas and is uncovered
 * as the current sheet peels from the right edge toward the left.
 *
 * The turn comes in three randomised variants (slowDramatic / mediumCrisp /
 * snapWithPeel) that vary duration, easing, curl depth, and an optional brief
 * skew-peel hesitation before the roll. See VARIANTS below.
 */
(function () {
  'use strict';

  const SEEN_KEY  = 'arjun_flip_seen';
  const DPR       = Math.min(window.devicePixelRatio || 1, 2);

  /* ── Cached viewport snapshot ─────────────────────────────────────────── */

  let snap = null;            // <canvas> bitmap of the current viewport
  let snapScrollY = 0;
  let snapping = false;
  let fallbackSnap = null;    // plain aged-paper sheet if html2canvas is absent

  function bodyBg() {
    const c = getComputedStyle(document.body).backgroundColor;
    return (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') ? c : '#f4f1ea';
  }

  function takeSnapshot() {
    if (!window.html2canvas) return Promise.resolve(null);
    if (snapping) return Promise.resolve(snap);
    snapping = true;
    const W = window.innerWidth, H = window.innerHeight;
    const sy = window.scrollY;
    return window.html2canvas(document.body, {
      x: window.scrollX, y: sy,
      width: W, height: H,
      scale: DPR,
      useCORS: true, allowTaint: true,
      backgroundColor: bodyBg(),
      logging: false, removeContainer: true,
    }).then(c => { snap = c; snapScrollY = sy; snapping = false; return c; })
      .catch(() => { snapping = false; return null; });
  }

  let snapTimer;
  function scheduleSnapshot() {
    clearTimeout(snapTimer);
    snapTimer = setTimeout(takeSnapshot, 220);
  }

  /* Aged-paper fallback sheet (only used if html2canvas failed to load). */
  function buildFallbackSnap() {
    const W = window.innerWidth, H = window.innerHeight;
    const c = document.createElement('canvas');
    c.width = Math.round(W * DPR); c.height = Math.round(H * DPR);
    const x = c.getContext('2d');
    x.scale(DPR, DPR);
    x.fillStyle = '#f1ece1';
    x.fillRect(0, 0, W, H);
    x.globalAlpha = 0.05;
    x.fillStyle = '#6b5a38';
    for (let i = 0; i < 1400; i++) {
      x.fillRect(Math.random() * W, Math.random() * H, 1.5, 1.5);
    }
    x.globalAlpha = 1;
    return c;
  }

  /* ── Render one frame of the peel ─────────────────────────────────────── *
   * p ∈ [0,1]:  0 = page flat (full content);  1 = page fully peeled away.
   * The contact line sweeps right→left; the lifted right portion curls up
   * and over toward the left as a single cylinder.
   */
  function draw(ctx, W, H, p, curl = 1) {
    ctx.clearRect(0, 0, W, H);
    const sheet = snap || fallbackSnap || (fallbackSnap = buildFallbackSnap());
    const sc = sheet.width / W;

    if (p <= 0.0006) { ctx.drawImage(sheet, 0, 0, sheet.width, sheet.height, 0, 0, W, H); return; }
    if (p >= 0.9994) return;

    const R  = Math.max(74, W * 0.14) * curl;     // curl radius (variant-scaled depth)
    // The fold sweeps from the right edge all the way PAST the left edge, so
    // the whole sheet rolls cleanly off-screen and the turn actually finishes
    // — rather than the canvas blanking out from under a leftover curl.
    const cx = W - p * (W + R + 48);              // fold line (right → off left)

    /* 1 ─ Flat, un-peeled remainder of the current page (real content). */
    if (cx > 0.5) {
      ctx.drawImage(sheet, 0, 0, Math.round(cx * sc), sheet.height, 0, 0, cx, H);
    }

    /* 2 ─ The curl. The lifted portion (source right of the fold) rolls UP
     *      and FORWARD — toward the viewer, projecting to the right of the
     *      fold — so the print stays in reading order. Strips are drawn from
     *      the far edge inward so the near, readable face lands on top. */
    const phiFree = (W - cx) / R;                 // angle at the free (right) edge
    const xEnd    = cx + R * Math.min(phiFree, Math.PI);
    const STEP    = 2;
    let curlRight = cx;                            // rightmost screen extent of the curl
    for (let x = xEnd; x > cx; x -= STEP) {
      const x0 = x - STEP;
      const s0 = cx + R * Math.sin((x0 - cx) / R);
      const s1 = cx + R * Math.sin((x  - cx) / R);
      const dx = Math.min(s0, s1);
      const dw = Math.max(0.7, Math.abs(s1 - s0)) + 0.6;
      const phi  = ((x0 + x) / 2 - cx) / R;
      const cosp = Math.cos(phi), sinp = Math.sin(phi);
      if (dx + dw > curlRight) curlRight = dx + dw;

      ctx.drawImage(sheet, x0 * sc, 0, STEP * sc, sheet.height, dx, 0, dw, H);

      if (cosp >= 0) {
        // front face: one shadow ramp, deepening as the paper rolls away
        const k = 0.55 * Math.pow(sinp, 1.2);
        if (k > 0.002) { ctx.fillStyle = `rgba(22,15,3,${k.toFixed(3)})`; ctx.fillRect(dx, 0, dw, H); }
      } else {
        // underside curling over: aged paper with a faint ghost of the print
        ctx.fillStyle = 'rgba(228,219,200,0.86)';
        ctx.fillRect(dx, 0, dw, H);
        const k = 0.42 + 0.26 * (-cosp);
        ctx.fillStyle = `rgba(16,10,2,${k.toFixed(3)})`;
        ctx.fillRect(dx, 0, dw, H);
      }
    }

    /* 3 ─ Soft shadow the lifted curl casts onto the revealed destination.
     *      Only while the curl is actually on screen, so it fades out as the
     *      sheet leaves rather than leaving a dark band behind. */
    if (curlRight > 1 && curlRight < W) {
      const st = Math.min(1, p * 1.6);
      const sw = Math.min(40 + 110 * st, W - curlRight);
      const g = ctx.createLinearGradient(curlRight, 0, curlRight + sw, 0);
      g.addColorStop(0, `rgba(12,8,2,${(0.32 * st + 0.05).toFixed(3)})`);
      g.addColorStop(0.5, `rgba(12,8,2,${(0.11 * st).toFixed(3)})`);
      g.addColorStop(1, 'rgba(12,8,2,0)');
      ctx.fillStyle = g;
      ctx.fillRect(curlRight, 0, sw, H);
    }

    /* 4 ─ Specular bend line where the sheet lifts off the surface. */
    if (cx > 0 && cx < W) {
      const lift = Math.min(1, p * 6);
      const lg = ctx.createLinearGradient(cx - 3, 0, cx + 4, 0);
      lg.addColorStop(0,   'rgba(255,251,238,0)');
      lg.addColorStop(0.4, `rgba(255,251,238,${(0.5 * lift).toFixed(3)})`);
      lg.addColorStop(1,   'rgba(255,251,238,0)');
      ctx.fillStyle = lg;
      ctx.fillRect(cx - 3, 0, 7, H);
    }
  }

  /* ── Easing & plumbing ────────────────────────────────────────────────── */

  const easeInOut = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const easeOut   = t => 1 - Math.pow(1 - t, 3);

  function makeCanvas() {
    const cv = document.createElement('canvas');
    cv.style.cssText =
      'position:fixed;inset:0;width:100%;height:100%;z-index:9995;pointer-events:none;';
    const W = window.innerWidth, H = window.innerHeight;
    cv.width = Math.round(W * DPR);
    cv.height = Math.round(H * DPR);
    const ctx = cv.getContext('2d');
    ctx.scale(DPR, DPR);
    document.body.appendChild(cv);
    return { cv, ctx, W, H };
  }

  /* ── Animation variants ───────────────────────────────────────────────── *
   * Three named profiles. One is chosen at random per turn (weighted toward
   * the dramatic turn on the very first navigation, equal thereafter).
   *   duration  total ms of the rolling motion (preDelay is on top)
   *   easingFn  eases p ∈ [0,1] over the roll
   *   preDelay  ms to hesitate (with a skew peel) before the roll begins
   *   peelSkew  skewX magnitude applied during the hesitation
   *   curl      curl-radius multiplier (< 1 = shallower, snappier curl)
   */
  const VARIANTS = {
    slowDramatic: { duration: 1100, easingFn: easeInOut, preDelay: 0,  peelSkew: 0,    curl: 1.0 },
    mediumCrisp:  { duration: 650,  easingFn: easeOut,   preDelay: 0,  peelSkew: 0,    curl: 0.7 },
    snapWithPeel: { duration: 900,  easingFn: easeInOut, preDelay: 80, peelSkew: 0.05, curl: 1.0 },
  };
  const VARIANT_NAMES = ['slowDramatic', 'mediumCrisp', 'snapWithPeel'];

  function pickVariant() {
    const firstTurn = !sessionStorage.getItem(SEEN_KEY);
    sessionStorage.setItem(SEEN_KEY, '1');
    if (firstTurn) {
      // 60 / 20 / 20 toward slowDramatic to preserve the memorable first impression.
      const r = Math.random();
      const name = r < 0.6 ? 'slowDramatic' : r < 0.8 ? 'mediumCrisp' : 'snapWithPeel';
      return VARIANTS[name];
    }
    return VARIANTS[VARIANT_NAMES[Math.floor(Math.random() * VARIANT_NAMES.length)]];
  }

  /* Brief pre-roll for snapWithPeel: the flat sheet leans with a slight skewX,
   * hinting the lift before the main curl begins. */
  function drawPrePeel(ctx, W, H, skew, t) {
    const sheet = snap || fallbackSnap || (fallbackSnap = buildFallbackSnap());
    const k = skew * Math.min(Math.max(t, 0), 1);
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = bodyBg();                     // fill first so the skew gap shows paper, not the destination
    ctx.fillRect(0, 0, W, H);
    ctx.save();
    ctx.transform(1, 0, -k, 1, 0, 0);             // skewX: the sheet leans as its right edge starts to lift
    ctx.drawImage(sheet, 0, 0, sheet.width, sheet.height, 0, 0, W, H);
    ctx.restore();
    // faint specular along the right edge where the lift begins
    const g = ctx.createLinearGradient(W - 64, 0, W, 0);
    g.addColorStop(0, 'rgba(255,251,238,0)');
    g.addColorStop(1, `rgba(255,251,238,${(0.35 * Math.min(t, 1)).toFixed(3)})`);
    ctx.fillStyle = g;
    ctx.fillRect(W - 64, 0, 64, H);
  }

  /* ── Exit: current page peels away, destination revealed beneath ──────── */

  let flipping = false;

  async function flipOut(href, variant) {
    if (flipping) return;
    flipping = true;

    // Tell the destination it is arriving via a flip, so it can skip its
    // entrance fade — otherwise the page snaps back to opacity 0 and re-fades
    // after the seamless reveal, which reads as a flash.
    try { sessionStorage.setItem('arjun_flip_at', String(Date.now())); } catch (e) {}

    // Make sure the snapshot matches what is on screen right now.
    if (!snap || Math.abs(window.scrollY - snapScrollY) > 4) await takeSnapshot();

    const ifr = document.createElement('iframe');
    ifr.style.cssText =
      'position:fixed;inset:0;border:none;width:100%;height:100%;z-index:9990;pointer-events:none;';
    ifr.src = href;
    document.body.appendChild(ifr);

    const o = makeCanvas();
    const { duration, easingFn, preDelay, peelSkew, curl } = variant;
    const t0 = performance.now();

    (function tick(now) {
      const elapsed = now - t0;
      if (elapsed < preDelay) {                       // hesitation + skew peel, before the roll
        drawPrePeel(o.ctx, o.W, o.H, peelSkew, elapsed / preDelay);
        requestAnimationFrame(tick);
        return;
      }
      const raw = Math.min((elapsed - preDelay) / duration, 1);
      draw(o.ctx, o.W, o.H, easingFn(raw), curl);
      if (raw < 1) requestAnimationFrame(tick);
      else window.location.href = href;
    }(performance.now()));
  }

  /* ── Init ─────────────────────────────────────────────────────────────── */

  function init() {
    // Pre-capture so the first click peels instantly; refresh after scroll.
    if (window.requestIdleCallback) requestIdleCallback(takeSnapshot, { timeout: 1200 });
    else setTimeout(takeSnapshot, 400);
    window.addEventListener('scroll', scheduleSnapshot, { passive: true });
    window.addEventListener('resize', () => { snap = null; fallbackSnap = null; scheduleSnapshot(); });

    document.addEventListener('click', function (e) {
      const link = e.target.closest('a[href]');
      if (!link) return;
      const href = link.getAttribute('href');
      if (!href
        || href.startsWith('#')
        || href.startsWith('http')
        || href.startsWith('//')
        || href.startsWith('mailto')
        || href.startsWith('tel')) return;

      e.preventDefault();
      flipOut(href, pickVariant());
    }, true);
  }

  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', init)
    : init();

}());
