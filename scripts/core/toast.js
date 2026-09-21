/**
 * scripts/core/toast.js - Notificações toast.
 */
window.CG = window.CG || {};

CG.toast = (function () {
    const COLORS = {
        success: 'bg-emerald-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-amber-500',
    };

    const ICONS = {
        success: 'ph-check-circle',
        error: 'ph-x-circle',
        info: 'ph-info',
        warning: 'ph-warning',
    };

    function show(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');

        toast.className = `${COLORS[type] || COLORS.info} text-white px-5 py-3 rounded-xl shadow-lg flex items-center gap-3 transform translate-x-full transition-transform duration-300 pointer-events-auto min-w-[280px]`;
        toast.innerHTML = `<i class="ph ${ICONS[type] || ICONS.info} text-xl"></i><span class="font-medium">${message}</span>`;

        container.appendChild(toast);

        // Anima a entrada
        requestAnimationFrame(() => toast.classList.remove('translate-x-full'));

        // Remove após 3s
        setTimeout(() => {
            toast.classList.add('translate-x-full', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    return { show };
})();
