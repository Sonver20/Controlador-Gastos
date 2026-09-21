/**
 * scripts/core/state.js - Estado global de navegação (compartilhado entre
 * features). Nada aqui toca no DOM nem chama a API: é só um namespace de
 * variáveis que antes viviam soltas no topo do script.js monolítico.
 */
window.CG = window.CG || {};

CG.state = {
    // Árvore de Gastos (drill-down)
    currentTreeMonth: null,
    currentTreeCategory: null,
    // null = sem filtro, "" = balde "sem subcategoria", "X" = subcategoria específica
    currentTreeSubcategory: null,
    // true se a grade de subcategorias foi exibida para a categoria atual
    currentTreeHasSubcategoryLevel: false,

    // Despesas Mensais: id do grupo em edição (null = novo grupo)
    editingMonthlyGroupId: null,
};
