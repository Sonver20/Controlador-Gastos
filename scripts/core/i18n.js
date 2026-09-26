/**
 * scripts/core/i18n.js - Internacionalização (PT / EN).
 *
 * Fonte única das traduções da interface. Elementos estáticos usam
 * atributos `data-i18n` (texto), `data-i18n-placeholder` ou
 * `data-i18n-title`, aplicados por `apply()`. Conteúdo gerado
 * dinamicamente (features/*.js) chama `CG.i18n.t(key, params)`
 * diretamente.
 *
 * Mensagens vindas do backend (services/*.py) trazem um campo opcional
 * `key` (e `params`) além do `message` em português: `showApiResult()`
 * procura a chave no dicionário `messages` e, se existir, usa a versão
 * traduzida; caso contrário cai para `res.message` (comportamento
 * anterior, nunca quebra).
 */
window.CG = window.CG || {};

CG.i18n = (function () {
    const MONTH_NAMES = {
        pt: ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'],
        en: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    };

    // Domingo (0) a Sábado (6) — usado pelo calendário customizado (CG.datepicker).
    const WEEKDAY_NAMES = {
        pt: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
        en: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    };

    const dict = {
        pt: {
            // Navegação
            'nav.dashboard': 'Dashboard',
            'nav.register': 'Nova Despesa',
            'nav.monthly': 'Despesas Mensais',
            'nav.tree': 'Árvore de Gastos',
            'nav.calendar': 'Calendário',

            // Cabeçalho
            'header.balance_label': 'Saldo',
            'header.edit_balance_title': 'Editar saldo',
            'header.theme_toggle_title': 'Alternar tema',

            // Configurações (engrenagem)
            'settings.title': 'Configurações',
            'settings.language_label': 'Idioma',
            'settings.color_label': 'Cor principal',
            'settings.color_custom_label': 'Personalizada',

            // Dashboard
            'dashboard.title': 'Dashboard',
            'dashboard.refresh_title': 'Atualizar',
            'dashboard.this_month': 'Este Mês',
            'dashboard.top_category': 'Maior Categoria',
            'dashboard.total_expenses': 'Total de Despesas',
            'dashboard.summary_title': 'Resumo Mensal',
            'dashboard.table_month': 'Mês',
            'dashboard.table_expenses': 'Despesas',
            'dashboard.table_total': 'Total',
            'dashboard.table_action': 'Ação',
            'dashboard.view_details': 'Ver detalhes →',
            'dashboard.no_expenses': 'Nenhuma despesa registrada ainda.',
            'dashboard.load_error': 'Erro ao carregar dashboard',

            // Nova Despesa
            'register.title': 'Nova Despesa',
            'register.category_label': 'Categoria',
            'register.category_placeholder': 'Ex: Alimentação, Transporte, Moradia...',
            'register.subcategory_label': 'Subcategoria (opcional)',
            'register.subcategory_placeholder': 'Ex: Assaí Atacadista, Carnes...',
            'register.products_label': 'Produtos',
            'register.add_product': 'Adicionar produto',
            'register.product_name_placeholder': 'Nome do produto',
            'register.product_price_placeholder': 'Preço',
            'register.remove_product_title': 'Remover produto',
            'register.total_label': 'Total',
            'register.save_button': 'Salvar Despesa',
            'register.clear_button': 'Limpar',
            'register.fill_correctly_warning': 'Verifique os produtos: nome, preço e quantidade são obrigatórios.',
            'register.add_one_warning': 'Adicione ao menos um produto.',
            'register.category_required_warning': 'Informe a categoria.',
            'register.comm_error': 'Erro de comunicação com o backend.',

            // Despesas Mensais
            'monthly.title': 'Despesas Mensais',
            'monthly.subtitle': 'Gastos fixos lançados e debitados do saldo automaticamente todo mês.',
            'monthly.new_button': 'Nova Despesa Mensal',
            'monthly.empty_title': 'Nenhuma despesa mensal cadastrada.',
            'monthly.empty_desc': 'Crie templates de gastos fixos (ex.: "Contas da casa", "Assinaturas") para serem lançados e debitados do saldo automaticamente todo mês.',
            'monthly.items_count': '{count} item(ns)',
            'monthly.applied_in': 'Aplicado em {month}',
            'monthly.pending': 'Pendente',
            'monthly.monthly_total': 'Total mensal',
            'monthly.edit_button': 'Editar',
            'monthly.apply_button': 'Aplicar agora',
            'monthly.apply_title': 'Lançar as despesas deste mês agora e debitar do saldo',
            'monthly.delete_button': 'Excluir',
            'monthly.load_error': 'Erro ao carregar despesas mensais.',
            'monthly.form_new_title': 'Nova Despesa Mensal',
            'monthly.form_edit_title': 'Editar Despesa Mensal',
            'monthly.back_to_list': '← Voltar à lista',
            'monthly.how_it_works_title': 'Como funciona',
            'monthly.how_it_works_desc': 'Cada item pode ter uma <strong>categoria diferente</strong>. Todo mês, ao abrir o app, todos os itens são lançados como despesas e o total é debitado do seu saldo automaticamente.',
            'monthly.name_label': 'Nome da despesa mensal',
            'monthly.name_placeholder': 'Ex: Contas da casa, Assinaturas, Mercado do mês',
            'monthly.items_label': 'Itens (cada um com sua categoria)',
            'monthly.add_item': 'Adicionar item',
            'monthly.remove_item_title': 'Remover item',
            'monthly.item_category_placeholder': 'Categoria (ex.: Moradia)',
            'monthly.item_subcategory_placeholder': 'Subcategoria (opcional)',
            'monthly.item_name_placeholder': 'Nome do produto / conta',
            'monthly.item_price_placeholder': 'Preço',
            'monthly.form_total_label': 'Total mensal',
            'monthly.save_button': 'Salvar Despesa Mensal',
            'monthly.cancel_button': 'Cancelar',
            'monthly.invalid_items_warning': 'Verifique os itens: categoria, nome, preço e quantidade são obrigatórios.',
            'monthly.add_one_item_warning': 'Adicione ao menos um item.',
            'monthly.save_error': 'Erro ao salvar despesa mensal.',
            'monthly.delete_error_generic': 'Erro ao excluir.',
            'monthly.apply_error_generic': 'Erro ao aplicar despesa mensal.',
            // mensagens vindas do backend (services/monthly.py)
            'monthly.name_required': 'Informe um nome para a despesa mensal.',
            'monthly.no_valid_items': 'Nenhum item válido. Cada item precisa de categoria, nome, preço e quantidade.',
            'monthly.created': "Despesa mensal '{name}' criada com {count} item(ns).",
            'monthly.create_error': 'Erro ao criar despesa mensal: {error}',
            'monthly.updated': "Despesa mensal '{name}' atualizada com {count} item(ns).",
            'monthly.update_error': 'Erro ao atualizar despesa mensal: {error}',
            'monthly.deleted': 'Despesa mensal excluída.',
            'monthly.delete_error': 'Erro ao excluir: {error}',
            'monthly.not_found': 'Despesa mensal não encontrada.',
            'monthly.apply_error': 'Erro ao lançar despesas: {error}',
            'monthly.applied': "'{name}' aplicada: {count} despesa(s), {total} debitado(s) do saldo.",
            'monthly.none_pending': 'Nenhuma despesa mensal pendente.',
            'monthly.check_applied': 'Despesas mensais lançadas: {groups} grupo(s), {inserted} despesa(s), {total} debitado(s) do saldo.',

            // Árvore de Gastos
            'tree.title': 'Árvore de Gastos',
            'tree.breadcrumb_months': 'Meses',
            'tree.back_to_months': '← Voltar aos meses',
            'tree.back_to_categories': '← Voltar às categorias',
            'tree.back': '← Voltar',
            'tree.no_expenses_recorded': 'Nenhuma despesa registrada.',
            'tree.load_months_error': 'Erro ao carregar meses.',
            'tree.no_category_found': 'Nenhuma categoria encontrada.',
            'tree.load_categories_error': 'Erro ao carregar categorias.',
            'tree.no_subcategory': 'Sem subcategoria',
            'tree.no_expense_found': 'Nenhuma despesa encontrada.',
            'tree.load_expenses_error': 'Erro ao carregar despesas.',
            'tree.table_date': 'Data',
            'tree.table_description': 'Descrição',
            'tree.table_value': 'Valor',
            'tree.table_actions': 'Ações',
            'tree.edit_title': 'Editar',
            'tree.delete_title': 'Excluir',
            'common.count_items': '{count} item(ns)',
            'common.count_expenses': '{count} despesa(s)',

            // Calendário
            'calendar.title': 'Calendário de Salários',
            'calendar.not_configured': 'Não configurado',
            'calendar.vacation_net': 'Férias (líquido)',
            'calendar.monthly_salary': 'Salário mensal',
            'calendar.next_badge': 'Próximo',
            'calendar.vacation_badge': 'Férias',
            'calendar.click_details': 'Clique para detalhes',
            'calendar.no_reference_msg': 'Configure a próxima data de recebimento do salário para ver o calendário.',
            'calendar.configure_now': 'Configurar agora',
            'calendar.load_error': 'Erro ao carregar calendário.',

            // Modal de Férias
            'ferias.title': 'Calcular Férias',
            'ferias.description': 'Informe o salário bruto para calcular o valor líquido das férias (inclui 1/3 constitucional, INSS e IRRF).',
            'ferias.gross_salary_label': 'Salário bruto (R$)',
            'ferias.calculate_button': 'Calcular',
            'ferias.invalid_salary_warning': 'Informe um salário válido.',
            'ferias.calc_error': 'Erro ao calcular.',
            'ferias.result_gross': 'Salário bruto:',
            'ferias.result_third': '1/3 constitucional:',
            'ferias.result_total_gross': 'Total bruto:',
            'ferias.result_inss': 'INSS:',
            'ferias.result_irrf_base': 'Base IRRF:',
            'ferias.result_irrf_calc': 'IRRF calculado:',
            'ferias.result_additional_discount': 'Desconto adicional:',
            'ferias.result_irrf_final': 'IRRF final:',
            'ferias.result_net': 'LÍQUIDO:',

            // Modal de Editar Despesa
            'edit_modal.title': 'Editar Despesa',
            'edit_modal.category': 'Categoria',
            'edit_modal.subcategory': 'Subcategoria (opcional)',
            'edit_modal.description': 'Descrição',
            'edit_modal.date': 'Data',
            'edit_modal.unit_price': 'Preço unitário (R$)',
            'edit_modal.quantity': 'Quantidade',
            'edit_modal.total_prefix': 'Total:',
            'edit_modal.save': 'Salvar Alterações',
            'edit_modal.cancel': 'Cancelar',
            'edit_modal.fill_correctly_warning': 'Preencha todos os campos corretamente.',
            'edit_modal.not_found_error': 'Despesa não encontrada.',
            'edit_modal.load_error': 'Erro ao carregar despesa.',
            'edit_modal.update_error_generic': 'Erro ao atualizar.',

            // Modal de Excluir
            'delete_modal.title': 'Confirmar Exclusão',
            'delete_modal.confirm_text': 'Tem certeza que deseja excluir esta despesa? Esta ação não pode ser desfeita.',
            'delete_modal.delete': 'Excluir',
            'delete_modal.cancel': 'Cancelar',
            'delete_modal.error_generic': 'Erro ao excluir.',

            // Modal de Saldo & Salário
            'balance_modal.title': 'Meu Saldo & Salário',
            'balance_modal.current_balance_label': 'Saldo Atual (R$)',
            'balance_modal.monthly_salary_label': 'Salário Mensal (R$)',
            'balance_modal.salary_placeholder': 'Ex: 3000,00',
            'balance_modal.auto_credit_hint': 'Crédito automático a cada 30 dias.',
            'balance_modal.next_date_label': 'Próxima data de recebimento',
            'balance_modal.next_date_hint': 'Usada para calcular os próximos recebimentos de 30 em 30 dias (os meses seguintes mudam de dia de acordo, já que nem todo mês tem o mesmo tamanho).',
            'balance_modal.vacation_month_label': 'Mês de Férias',
            'balance_modal.vacation_hint': 'No calendário, o recebimento que cair nesse mês mostrará o valor líquido das férias.',
            'balance_modal.save': 'Salvar',
            'balance_modal.cancel': 'Cancelar',
            'balance_modal.salary_current_prefix': 'Salário atual: {amount}',
            'balance_modal.no_salary_configured': 'Nenhum salário configurado',
            'balance_modal.invalid_values_warning': 'Informe valores válidos.',
            'balance_modal.save_generic_error': 'Erro ao salvar.',
            'balance_modal.save_success': 'Saldo, salário e mês de férias atualizados!',

            // mensagens vindas do backend (services/finance.py, scheduler.py, database.py)
            'expense.add.success': 'Despesa registrada com sucesso!',
            'expense.add.error': 'Erro ao salvar: {error}',
            'expense.update.success': 'Despesa atualizada com sucesso!',
            'expense.update.error': 'Erro ao atualizar: {error}',
            'expense.delete.success': 'Despesa excluída com sucesso!',
            'expense.delete.error': 'Erro ao excluir: {error}',
            'expense.not_found': 'Despesa não encontrada.',
            'validation.invalid_value': "Valor inválido: '{value}'",
            'validation.invalid_date': 'Data inválida.',
            'balance.updated': 'Saldo atualizado.',
            'balance.update_error': 'Erro ao atualizar saldo: {error}',
            'expenses.batch.error': 'Erro em massa: {error}',
            'expenses.bulk.result': '{inserted} despesa(s) inserida(s). {errors_count} erro(s) encontrado(s).',
            'expenses.structured.result': '{inserted} despesa(s) registrada(s).',
            'salary.configured': 'Salário configurado.',
            'salary.configure_error': 'Erro ao configurar salário: {error}',
            'salary.not_configured': 'Salário não configurado.',
            'salary.credited': 'Salário de {amount} creditado.',
            'salary.credit_error': 'Erro ao creditar salário: {error}',
            'salary.next_date_updated': 'Data de recebimento atualizada.',
            'salary.next_date_error': 'Erro ao atualizar data: {error}',

            'main.init_error': 'Erro de inicialização do app.',

            'months.1': 'Janeiro', 'months.2': 'Fevereiro', 'months.3': 'Março', 'months.4': 'Abril',
            'months.5': 'Maio', 'months.6': 'Junho', 'months.7': 'Julho', 'months.8': 'Agosto',
            'months.9': 'Setembro', 'months.10': 'Outubro', 'months.11': 'Novembro', 'months.12': 'Dezembro',
        },
        en: {
            'nav.dashboard': 'Dashboard',
            'nav.register': 'New Expense',
            'nav.monthly': 'Monthly Expenses',
            'nav.tree': 'Expense Tree',
            'nav.calendar': 'Calendar',

            'header.balance_label': 'Balance',
            'header.edit_balance_title': 'Edit balance',
            'header.theme_toggle_title': 'Toggle theme',

            'settings.title': 'Settings',
            'settings.language_label': 'Language',
            'settings.color_label': 'Primary color',
            'settings.color_custom_label': 'Custom',

            'dashboard.title': 'Dashboard',
            'dashboard.refresh_title': 'Refresh',
            'dashboard.this_month': 'This Month',
            'dashboard.top_category': 'Top Category',
            'dashboard.total_expenses': 'Total Expenses',
            'dashboard.summary_title': 'Monthly Summary',
            'dashboard.table_month': 'Month',
            'dashboard.table_expenses': 'Expenses',
            'dashboard.table_total': 'Total',
            'dashboard.table_action': 'Action',
            'dashboard.view_details': 'View details →',
            'dashboard.no_expenses': 'No expenses recorded yet.',
            'dashboard.load_error': 'Error loading dashboard',

            'register.title': 'New Expense',
            'register.category_label': 'Category',
            'register.category_placeholder': 'E.g.: Food, Transportation, Housing...',
            'register.subcategory_label': 'Subcategory (optional)',
            'register.subcategory_placeholder': 'E.g.: Costco, Meat...',
            'register.products_label': 'Products',
            'register.add_product': 'Add product',
            'register.product_name_placeholder': 'Product name',
            'register.product_price_placeholder': 'Price',
            'register.remove_product_title': 'Remove product',
            'register.total_label': 'Total',
            'register.save_button': 'Save Expense',
            'register.clear_button': 'Clear',
            'register.fill_correctly_warning': 'Check the products: name, price and quantity are required.',
            'register.add_one_warning': 'Add at least one product.',
            'register.category_required_warning': 'Enter the category.',
            'register.comm_error': 'Communication error with the backend.',

            'monthly.title': 'Monthly Expenses',
            'monthly.subtitle': 'Fixed expenses launched and automatically debited from your balance every month.',
            'monthly.new_button': 'New Monthly Expense',
            'monthly.empty_title': 'No monthly expenses registered.',
            'monthly.empty_desc': 'Create fixed-expense templates (e.g. "Household bills", "Subscriptions") to be launched and debited from your balance automatically every month.',
            'monthly.items_count': '{count} item(s)',
            'monthly.applied_in': 'Applied in {month}',
            'monthly.pending': 'Pending',
            'monthly.monthly_total': 'Monthly total',
            'monthly.edit_button': 'Edit',
            'monthly.apply_button': 'Apply now',
            'monthly.apply_title': "Launch this month's expenses now and debit the balance",
            'monthly.delete_button': 'Delete',
            'monthly.load_error': 'Error loading monthly expenses.',
            'monthly.form_new_title': 'New Monthly Expense',
            'monthly.form_edit_title': 'Edit Monthly Expense',
            'monthly.back_to_list': '← Back to list',
            'monthly.how_it_works_title': 'How it works',
            'monthly.how_it_works_desc': 'Each item can have a <strong>different category</strong>. Every month, when you open the app, all items are launched as expenses and the total is automatically debited from your balance.',
            'monthly.name_label': 'Monthly expense name',
            'monthly.name_placeholder': 'E.g.: Household bills, Subscriptions, Monthly groceries',
            'monthly.items_label': 'Items (each with its own category)',
            'monthly.add_item': 'Add item',
            'monthly.remove_item_title': 'Remove item',
            'monthly.item_category_placeholder': 'Category (e.g.: Housing)',
            'monthly.item_subcategory_placeholder': 'Subcategory (optional)',
            'monthly.item_name_placeholder': 'Product / bill name',
            'monthly.item_price_placeholder': 'Price',
            'monthly.form_total_label': 'Monthly total',
            'monthly.save_button': 'Save Monthly Expense',
            'monthly.cancel_button': 'Cancel',
            'monthly.invalid_items_warning': 'Check the items: category, name, price and quantity are required.',
            'monthly.add_one_item_warning': 'Add at least one item.',
            'monthly.save_error': 'Error saving monthly expense.',
            'monthly.delete_error_generic': 'Error deleting.',
            'monthly.apply_error_generic': 'Error applying monthly expense.',
            'monthly.name_required': 'Enter a name for the monthly expense.',
            'monthly.no_valid_items': 'No valid items. Each item needs a category, name, price and quantity.',
            'monthly.created': "Monthly expense '{name}' created with {count} item(s).",
            'monthly.create_error': 'Error creating monthly expense: {error}',
            'monthly.updated': "Monthly expense '{name}' updated with {count} item(s).",
            'monthly.update_error': 'Error updating monthly expense: {error}',
            'monthly.deleted': 'Monthly expense deleted.',
            'monthly.delete_error': 'Error deleting: {error}',
            'monthly.not_found': 'Monthly expense not found.',
            'monthly.apply_error': 'Error launching expenses: {error}',
            'monthly.applied': "'{name}' applied: {count} expense(s), {total} debited from your balance.",
            'monthly.none_pending': 'No pending monthly expenses.',
            'monthly.check_applied': 'Monthly expenses launched: {groups} group(s), {inserted} expense(s), {total} debited from your balance.',

            'tree.title': 'Expense Tree',
            'tree.breadcrumb_months': 'Months',
            'tree.back_to_months': '← Back to months',
            'tree.back_to_categories': '← Back to categories',
            'tree.back': '← Back',
            'tree.no_expenses_recorded': 'No expenses recorded.',
            'tree.load_months_error': 'Error loading months.',
            'tree.no_category_found': 'No category found.',
            'tree.load_categories_error': 'Error loading categories.',
            'tree.no_subcategory': 'No subcategory',
            'tree.no_expense_found': 'No expense found.',
            'tree.load_expenses_error': 'Error loading expenses.',
            'tree.table_date': 'Date',
            'tree.table_description': 'Description',
            'tree.table_value': 'Value',
            'tree.table_actions': 'Actions',
            'tree.edit_title': 'Edit',
            'tree.delete_title': 'Delete',
            'common.count_items': '{count} item(s)',
            'common.count_expenses': '{count} expense(s)',

            'calendar.title': 'Salary Calendar',
            'calendar.not_configured': 'Not configured',
            'calendar.vacation_net': 'Vacation (net)',
            'calendar.monthly_salary': 'Monthly salary',
            'calendar.next_badge': 'Next',
            'calendar.vacation_badge': 'Vacation',
            'calendar.click_details': 'Click for details',
            'calendar.no_reference_msg': 'Set your next salary payment date to see the calendar.',
            'calendar.configure_now': 'Configure now',
            'calendar.load_error': 'Error loading calendar.',

            'ferias.title': 'Calculate Vacation Pay',
            'ferias.description': 'Enter the gross salary to calculate the net vacation pay (includes the constitutional 1/3 bonus, INSS and IRRF).',
            'ferias.gross_salary_label': 'Gross salary (R$)',
            'ferias.calculate_button': 'Calculate',
            'ferias.invalid_salary_warning': 'Enter a valid salary.',
            'ferias.calc_error': 'Error calculating.',
            'ferias.result_gross': 'Gross salary:',
            'ferias.result_third': 'Constitutional 1/3:',
            'ferias.result_total_gross': 'Total gross:',
            'ferias.result_inss': 'INSS:',
            'ferias.result_irrf_base': 'IRRF base:',
            'ferias.result_irrf_calc': 'IRRF calculated:',
            'ferias.result_additional_discount': 'Additional discount:',
            'ferias.result_irrf_final': 'Final IRRF:',
            'ferias.result_net': 'NET:',

            'edit_modal.title': 'Edit Expense',
            'edit_modal.category': 'Category',
            'edit_modal.subcategory': 'Subcategory (optional)',
            'edit_modal.description': 'Description',
            'edit_modal.date': 'Date',
            'edit_modal.unit_price': 'Unit price (R$)',
            'edit_modal.quantity': 'Quantity',
            'edit_modal.total_prefix': 'Total:',
            'edit_modal.save': 'Save Changes',
            'edit_modal.cancel': 'Cancel',
            'edit_modal.fill_correctly_warning': 'Fill in all fields correctly.',
            'edit_modal.not_found_error': 'Expense not found.',
            'edit_modal.load_error': 'Error loading expense.',
            'edit_modal.update_error_generic': 'Error updating.',

            'delete_modal.title': 'Confirm Deletion',
            'delete_modal.confirm_text': 'Are you sure you want to delete this expense? This action cannot be undone.',
            'delete_modal.delete': 'Delete',
            'delete_modal.cancel': 'Cancel',
            'delete_modal.error_generic': 'Error deleting.',

            'balance_modal.title': 'My Balance & Salary',
            'balance_modal.current_balance_label': 'Current Balance (R$)',
            'balance_modal.monthly_salary_label': 'Monthly Salary (R$)',
            'balance_modal.salary_placeholder': 'E.g.: 3000.00',
            'balance_modal.auto_credit_hint': 'Automatic credit every 30 days.',
            'balance_modal.next_date_label': 'Next payment date',
            'balance_modal.next_date_hint': 'Used to calculate the next payments every 30 days (following months shift day accordingly, since not every month has the same length).',
            'balance_modal.vacation_month_label': 'Vacation Month',
            'balance_modal.vacation_hint': 'In the calendar, the payment that falls in this month will show the net vacation pay.',
            'balance_modal.save': 'Save',
            'balance_modal.cancel': 'Cancel',
            'balance_modal.salary_current_prefix': 'Current salary: {amount}',
            'balance_modal.no_salary_configured': 'No salary configured',
            'balance_modal.invalid_values_warning': 'Enter valid values.',
            'balance_modal.save_generic_error': 'Error saving.',
            'balance_modal.save_success': 'Balance, salary and vacation month updated!',

            'expense.add.success': 'Expense recorded successfully!',
            'expense.add.error': 'Error saving: {error}',
            'expense.update.success': 'Expense updated successfully!',
            'expense.update.error': 'Error updating: {error}',
            'expense.delete.success': 'Expense deleted successfully!',
            'expense.delete.error': 'Error deleting: {error}',
            'expense.not_found': 'Expense not found.',
            'validation.invalid_value': "Invalid value: '{value}'",
            'validation.invalid_date': 'Invalid date.',
            'balance.updated': 'Balance updated.',
            'balance.update_error': 'Error updating balance: {error}',
            'expenses.batch.error': 'Batch error: {error}',
            'expenses.bulk.result': '{inserted} expense(s) inserted. {errors_count} error(s) found.',
            'expenses.structured.result': '{inserted} expense(s) recorded.',
            'salary.configured': 'Salary configured.',
            'salary.configure_error': 'Error configuring salary: {error}',
            'salary.not_configured': 'Salary not configured.',
            'salary.credited': 'Salary of {amount} credited.',
            'salary.credit_error': 'Error crediting salary: {error}',
            'salary.next_date_updated': 'Payment date updated.',
            'salary.next_date_error': 'Error updating date: {error}',

            'main.init_error': 'App initialization error.',

            'months.1': 'January', 'months.2': 'February', 'months.3': 'March', 'months.4': 'April',
            'months.5': 'May', 'months.6': 'June', 'months.7': 'July', 'months.8': 'August',
            'months.9': 'September', 'months.10': 'October', 'months.11': 'November', 'months.12': 'December',
        },
    };

    // Chaves para as quais um param numérico deve ser formatado como
    // moeda (R$) antes de entrar no texto interpolado.
    const MONEY_PARAM_KEYS = new Set(['amount', 'total']);

    let currentLang = 'pt';

    function interpolate(str, params) {
        if (!params) return str;
        return str.replace(/\{(\w+)\}/g, (match, key) => {
            if (!(key in params)) return match;
            let value = params[key];
            if (MONEY_PARAM_KEYS.has(key) && value !== null && value !== undefined && CG.utils) {
                value = CG.utils.formatCurrency(Number(value));
            }
            return value;
        });
    }

    /** Traduz uma chave para o idioma atual. */
    function t(key, params) {
        const str = (dict[currentLang] && dict[currentLang][key]) || (dict.pt && dict.pt[key]) || key;
        return interpolate(str, params);
    }

    function getLanguage() {
        return currentLang;
    }

    /** Nome do mês (1-12) no idioma atual — usado por CG.utils.formatMonth. */
    function monthName(monthIndex1to12) {
        return (MONTH_NAMES[currentLang] || MONTH_NAMES.pt)[monthIndex1to12 - 1];
    }

    /** Abreviação do dia da semana (0=domingo .. 6=sábado) no idioma atual. */
    function weekdayShort(index0to6) {
        return (WEEKDAY_NAMES[currentLang] || WEEKDAY_NAMES.pt)[index0to6];
    }

    /** Locale do Intl/Date a usar no idioma atual (formatação de datas). */
    function locale() {
        return currentLang === 'en' ? 'en-US' : 'pt-BR';
    }

    /**
     * Aplica as traduções a todos os elementos com data-i18n /
     * data-i18n-placeholder / data-i18n-title no documento, e ajusta
     * document.documentElement.lang.
     */
    function apply() {
        document.documentElement.lang = currentLang === 'en' ? 'en' : 'pt-BR';
        document.querySelectorAll('[data-i18n]').forEach(el => {
            el.innerHTML = t(el.getAttribute('data-i18n'));
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
        });
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            el.title = t(el.getAttribute('data-i18n-title'));
        });
    }

    /**
     * Re-renderiza o conteúdo dinâmico da view atualmente visível, para
     * que a troca de idioma reflita imediatamente sem precisar navegar.
     * Feito com checagens defensivas (each feature pode não ter
     * carregado ainda / não ter nada para recarregar).
     */
    function refreshDynamicContent() {
        try { CG.dashboard && CG.dashboard.load(); } catch (e) { /* view pode não estar visível ainda */ }
        try { CG.monthly && CG.monthly.renderList && !document.getElementById('monthly-list-view').classList.contains('hidden') && CG.monthly.renderList(); } catch (e) { }
        try { CG.tree && CG.tree.refreshCurrentView && CG.tree.refreshCurrentView(); } catch (e) { }
        try { CG.calendar && CG.calendar.render(); } catch (e) { }
        try { CG.balance && CG.balance.load(); } catch (e) { }
    }

    async function init() {
        try {
            const res = await CG.api.call('get_language');
            currentLang = (res.success && res.language === 'en') ? 'en' : 'pt';
        } catch (e) {
            console.error('Falha ao carregar idioma:', e);
        }
        apply();
    }

    async function setLanguage(lang) {
        currentLang = lang === 'en' ? 'en' : 'pt';
        apply();
        refreshDynamicContent();
        try {
            await CG.api.call('set_language', currentLang);
        } catch (e) {
            console.error('Falha ao salvar idioma:', e);
        }
    }

    /**
     * Mostra um toast a partir de um resultado da API (res.success,
     * res.message, res.key opcional, res.params opcional). Usa a
     * tradução de res.key quando existir; caso contrário cai para
     * res.message (texto em português vindo do backend), garantindo que
     * nada quebre para mensagens ainda não mapeadas.
     */
    function showApiResult(res, type) {
        if (!res) return;
        const kind = type || (res.success ? 'success' : 'error');
        let msg = res.message;
        if (res.key && dict[currentLang] && dict[currentLang][res.key]) {
            msg = interpolate(dict[currentLang][res.key], res.params);
        }
        CG.toast.show(msg, kind);
    }

    return { init, apply, t, setLanguage, getLanguage, monthName, weekdayShort, locale, showApiResult, refreshDynamicContent };
})();
