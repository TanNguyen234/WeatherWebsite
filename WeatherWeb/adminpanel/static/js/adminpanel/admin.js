/**
 * adminpanel/admin.js
 * Shared admin panel utilities.
 * Page-specific JS lives inline in each template.
 */
(function () {
    "use strict";

    /* ── Auto-dismiss flash messages ────────────────────────── */
    document.querySelectorAll('[data-auto-dismiss]').forEach(function (el) {
        var delay = parseInt(el.dataset.autoDismiss, 10) || 4000;
        setTimeout(function () {
            el.style.transition = 'opacity .4s';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 400);
        }, delay);
    });

    /* ── Confirm-before-submit buttons ──────────────────────── */
    document.querySelectorAll('[data-confirm]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!window.confirm(btn.dataset.confirm)) {
                e.preventDefault();
                e.stopImmediatePropagation();
            }
        });
    });

}());
