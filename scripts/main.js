/**
 * scripts/main.js - Ponto de entrada do frontend.
 * Navegação entre views, atalhos de teclado e inicialização do app.
 */
window.CG = window.CG || {};

(function () {
    const toast = CG.toast;

    // ==========================================================================
    // NAVEGAÇÃO
    // ==========================================================================
    function switchView(viewId) {
        document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
        document.getElementById(viewId).classList.remove('hidden');

        // Carrega dados ao entrar em views específicas
        if (viewId === 'view-dashboard') CG.dashboard.load();
        if (viewId === 'view-tree') CG.tree.showMonthsList();
        if (viewId === 'view-register') CG.register.onEnterView();
        if (viewId === 'view-calendar') CG.calendar.render();
        if (viewId === 'view-monthly') CG.monthly.onEnterView();
    }

    function setActiveButton(btn) {
        document.querySelectorAll('.nav-btn').forEach(b => {
            b.classList.remove('bg-primary-50', 'text-primary-700', 'dark:bg-primary-900/30', 'dark:text-primary-300', 'font-medium');
            b.classList.add('text-slate-600', 'dark:text-slate-300');
        });
        btn.classList.remove('text-slate-600', 'dark:text-slate-300');
        btn.classList.add('bg-primary-50', 'text-primary-700', 'dark:bg-primary-900/30', 'dark:text-primary-300', 'font-medium');
    }

    function initNavigation() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                switchView(btn.dataset.target);
                setActiveButton(btn);
            });
        });
    }

    // ==========================================================================
    // ATALHOS DE TECLADO
    // ==========================================================================
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                CG.modals.closeEdit();
                CG.modals.closeDelete();
                CG.balance.closeModal();
                CG.calendar.closeFeriasModal();
            }
        });
    }

    // ==========================================================================
    // VERSÃO DO APP
    // ==========================================================================
    async function loadAppVersion() {
        try {
            const res = await CG.api.call('get_app_version');
            const footer = document.getElementById('app-version-footer');
            if (res.success && footer) {
                footer.innerHTML = `Controlador de Gastos v${res.version}<br>PyWebView Desktop`;
            }
        } catch (e) {
            console.error('Erro ao carregar versão:', e);
        }
    }

    // ==========================================================================
    // AUTO SALÁRIO (a cada 30 dias)
    // ==========================================================================
    async function checkAutoSalary() {
        try {
            const res = await CG.api.call('check_auto_salary');
            if (res.success && res.should_credit) {
                CG.i18n.showApiResult(res, 'success');
                CG.balance.load();
            }
        } catch (e) {
            console.error('Erro na verificação de salário automático:', e);
        }
    }

    // ==========================================================================
    // INIT
    // ==========================================================================
    document.addEventListener('DOMContentLoaded', () => {
        initNavigation();
        initKeyboardShortcuts();

        // Aguarda a ponte pywebview ficar pronta antes de chamar QUALQUER
        // método do backend.
        CG.api.waitReady().then(async () => {
            CG.theme.init();
            await CG.settings.init(); // idioma (CG.i18n) + cor principal (CG.color)
            CG.balance.load();      // saldo no header
            CG.dashboard.load();
            CG.register.loadCategoryList();
            CG.register.loadSubcategoryList();
            checkAutoSalary();      // crédito automático de salário
            CG.monthly.checkAuto(); // lançamento automático de despesas mensais
            loadAppVersion();
        }).catch(() => {
            toast.show(CG.i18n.t('main.init_error'), 'error');
        });
    });
})();
