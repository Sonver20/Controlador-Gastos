/**
 * scripts/core/datepicker.js - Seletor de data customizado.
 *
 * Substitui <input type="date"> nativo: campos desse tipo são exibidos
 * pelo WebKitGTK no formato do idioma/localidade do SISTEMA OPERACIONAL,
 * não no idioma escolhido dentro do app (mesmo com document.lang setado
 * corretamente) — não existe forma confiável de controlar isso via CSS/JS
 * em cima do input nativo. A solução é este calendário próprio: o campo
 * vira um <input type="text" readonly>, o valor real (ISO "YYYY-MM-DD")
 * fica em data-iso, e o texto exibido é formatado por
 * CG.utils.formatDateBR (que já segue o idioma atual).
 */
window.CG = window.CG || {};

CG.datepicker = (function () {
    let openPopover = null;
    let openInputId = null;

    function pad2(n) { return String(n).padStart(2, '0'); }

    function isoOf(year, month0, day) {
        return `${year}-${pad2(month0 + 1)}-${pad2(day)}`;
    }

    function closePopover() {
        if (openPopover) {
            openPopover.remove();
            openPopover = null;
            openInputId = null;
        }
    }

    function displayValue(input) {
        const iso = input.dataset.iso || '';
        input.value = iso ? CG.utils.formatDateBR(iso) : '';
    }

    function renderCalendar(input, viewYear, viewMonth0) {
        const selectedIso = input.dataset.iso || '';
        const todayIso = isoOf(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());

        const firstOfMonth = new Date(viewYear, viewMonth0, 1);
        const startWeekday = firstOfMonth.getDay(); // 0 = domingo
        const daysInMonth = new Date(viewYear, viewMonth0 + 1, 0).getDate();
        const daysInPrevMonth = new Date(viewYear, viewMonth0, 0).getDate();

        let cells = '';
        // Dias do mês anterior (esmaecidos, preenchendo a primeira semana)
        for (let i = 0; i < startWeekday; i++) {
            const d = daysInPrevMonth - startWeekday + 1 + i;
            cells += `<span class="text-slate-300 dark:text-slate-600 text-sm py-1.5 rounded-lg">${d}</span>`;
        }
        // Dias do mês atual
        for (let d = 1; d <= daysInMonth; d++) {
            const iso = isoOf(viewYear, viewMonth0, d);
            const isSelected = iso === selectedIso;
            const isToday = iso === todayIso;
            const cls = isSelected
                ? 'bg-primary-600 text-white font-semibold'
                : isToday
                    ? 'border border-primary-400 dark:border-primary-600 text-primary-700 dark:text-primary-300'
                    : 'hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200';
            cells += `<button type="button" data-iso="${iso}" class="cg-dp-day text-sm py-1.5 rounded-lg transition ${cls}">${d}</button>`;
        }
        // Preenche o restante da grade com dias do próximo mês (esmaecidos)
        const totalCells = startWeekday + daysInMonth;
        const trailing = (7 - (totalCells % 7)) % 7;
        for (let d = 1; d <= trailing; d++) {
            cells += `<span class="text-slate-300 dark:text-slate-600 text-sm py-1.5 rounded-lg">${d}</span>`;
        }

        const weekdayHeaders = [0, 1, 2, 3, 4, 5, 6]
            .map(i => `<span class="text-xs font-semibold text-slate-400 py-1">${CG.i18n.weekdayShort(i)}</span>`)
            .join('');

        return `
            <div class="flex items-center justify-between mb-2">
                <button type="button" class="cg-dp-prev p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition">
                    <i class="ph ph-caret-left"></i>
                </button>
                <span class="text-sm font-semibold capitalize">${CG.i18n.monthName(viewMonth0 + 1)} ${viewYear}</span>
                <button type="button" class="cg-dp-next p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition">
                    <i class="ph ph-caret-right"></i>
                </button>
            </div>
            <div class="grid grid-cols-7 gap-0.5 text-center mb-1">${weekdayHeaders}</div>
            <div class="grid grid-cols-7 gap-0.5 text-center">${cells}</div>
        `;
    }

    function positionPopover(pop, input) {
        const rect = input.getBoundingClientRect();
        const popWidth = 272; // ~17rem
        let left = rect.left;
        if (left + popWidth > window.innerWidth - 8) left = window.innerWidth - popWidth - 8;
        pop.style.left = `${Math.max(8, left)}px`;
        // Abre para cima se não houver espaço suficiente abaixo (comum em
        // modais, onde o campo de data costuma ficar perto do rodapé).
        const spaceBelow = window.innerHeight - rect.bottom;
        if (spaceBelow < 320) {
            pop.style.top = `${rect.top - 8}px`;
            pop.style.transform = 'translateY(-100%)';
        } else {
            pop.style.top = `${rect.bottom + 8}px`;
            pop.style.transform = 'none';
        }
    }

    function open(inputId) {
        if (openInputId === inputId) { closePopover(); return; }
        closePopover();

        const input = document.getElementById(inputId);
        if (!input) return;

        const iso = input.dataset.iso;
        const base = iso ? new Date(iso + 'T00:00:00') : new Date();
        let viewYear = base.getFullYear();
        let viewMonth0 = base.getMonth();

        const pop = document.createElement('div');
        pop.className = 'cg-datepicker-popover fixed z-[9999] w-[17rem] bg-card-light dark:bg-card-dark rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 p-3';
        pop.innerHTML = renderCalendar(input, viewYear, viewMonth0);
        document.body.appendChild(pop);
        positionPopover(pop, input);

        function rerender() {
            pop.innerHTML = renderCalendar(input, viewYear, viewMonth0);
        }

        pop.addEventListener('click', (e) => {
            e.stopPropagation();
            const dayBtn = e.target.closest('.cg-dp-day');
            if (dayBtn) {
                input.dataset.iso = dayBtn.dataset.iso;
                displayValue(input);
                input.dispatchEvent(new Event('change', { bubbles: true }));
                closePopover();
                return;
            }
            if (e.target.closest('.cg-dp-prev')) {
                viewMonth0--;
                if (viewMonth0 < 0) { viewMonth0 = 11; viewYear--; }
                rerender();
                return;
            }
            if (e.target.closest('.cg-dp-next')) {
                viewMonth0++;
                if (viewMonth0 > 11) { viewMonth0 = 0; viewYear++; }
                rerender();
                return;
            }
        });

        openPopover = pop;
        openInputId = inputId;
    }

    /** Prepara um <input> existente para funcionar como seletor de data. */
    function attach(inputId) {
        const input = document.getElementById(inputId);
        if (!input) return;
        input.readOnly = true;
        input.classList.add('cursor-pointer');
        input.addEventListener('click', () => open(inputId));
    }

    /** Define o valor (ISO "YYYY-MM-DD", ou '' para limpar). */
    function setValue(inputId, isoDateStr) {
        const input = document.getElementById(inputId);
        if (!input) return;
        input.dataset.iso = isoDateStr || '';
        displayValue(input);
    }

    /** Lê o valor atual em ISO "YYYY-MM-DD" (ou '' se vazio). */
    function getValue(inputId) {
        const input = document.getElementById(inputId);
        return input ? (input.dataset.iso || '') : '';
    }

    document.addEventListener('click', () => closePopover());
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closePopover();
    });

    return { attach, setValue, getValue };
})();
