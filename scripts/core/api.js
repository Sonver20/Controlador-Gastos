/**
 * scripts/core/api.js - Wrapper em volta de pywebview.api.
 *
 * Centraliza o acesso ao backend Python: espera a ponte ficar pronta
 * (com timeout e retry), trata erros de comunicação de forma uniforme e
 * padroniza logs. Nenhum outro módulo deve chamar `pywebview.api`
 * diretamente.
 */
window.CG = window.CG || {};

CG.api = (function () {
    const CHECK_INTERVAL_MS = 100;
    const DEFAULT_TIMEOUT_MS = 10000; // 10s

    /**
     * Retorna uma Promise que resolve quando `pywebview.api` estiver
     * disponível, ou rejeita após `timeoutMs`.
     */
    function waitReady(timeoutMs = DEFAULT_TIMEOUT_MS) {
        return new Promise((resolve, reject) => {
            if (typeof pywebview !== 'undefined' && pywebview.api) {
                resolve();
                return;
            }
            let elapsed = 0;
            const interval = setInterval(() => {
                if (typeof pywebview !== 'undefined' && pywebview.api) {
                    clearInterval(interval);
                    resolve();
                    return;
                }
                elapsed += CHECK_INTERVAL_MS;
                if (elapsed >= timeoutMs) {
                    clearInterval(interval);
                    reject(new Error('pywebview.api não ficou disponível a tempo.'));
                }
            }, CHECK_INTERVAL_MS);
        });
    }

    /**
     * Chama um método do backend: `await CG.api.call('get_balance')`.
     * Levanta exceção em caso de falha de comunicação — quem chama decide
     * como apresentar o erro (toast etc.).
     */
    async function call(method, ...args) {
        await waitReady();
        try {
            return await pywebview.api[method](...args);
        } catch (e) {
            console.error(`API.${method} falhou:`, e);
            throw e;
        }
    }

    return { call, waitReady };
})();
