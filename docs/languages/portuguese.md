# 🇧🇷 Tradução para Português (Brasil) das Strings do Aplicativo

## Categoria 1: Autenticação e Gerenciamento de Conta (32 Strings)

| # | String em Inglês (English String) | Tradução em Português (Portuguese Translation) |
| :--- | :--- | :--- |
| 1. | Sign up | Cadastrar |
| 2. | Login to start | Entrar para começar |
| 3. | Email preferences updated successfully. | Preferências de e-mail atualizadas com sucesso. |
| 4. | There was an error updating your email preferences. | Ocorreu um erro ao atualizar suas preferências de e-mail. |
| 5. | Authenticated: login required · Public: open link · Unlisted: secret link · Invite token: one-time codes | Autenticado: requer login · Público: link aberto · Não listado: link secreto · Token de convite: códigos de uso único |
| 6. | Admin login | Login de administrador |
| 7. | Username | Nome de usuário |
| 8. | Password | Senha |
| 9. | Forgotten your password or username? | Esqueceu sua senha ou nome de usuário? |
| 10. | Logout | Sair |
| 11. | Forgot password? | Esqueceu a senha? |
| 12. | Password updated | Senha atualizada |
| 13. | Your password has been changed successfully. | Sua senha foi alterada com sucesso. |
| 14. | Change password | Alterar senha |
| 15. | Change your password | Altere sua senha |
| 16. | Save new password | Salvar nova senha |
| 17. | Password reset complete | Redefinição de senha concluída |
| 18. | Your password has been set. You can now log in with your new password. | Sua senha foi definida. Agora você pode entrar com sua nova senha. |
| 19. | Go to login | Ir para o login |
| 20. | This password reset link is invalid or has expired. | Este link de redefinição de senha é inválido ou expirou. |
| 21. | Reset email sent | E-mail de redefinição enviado |
| 22. | Check your email | Verifique seu e-mail |
| 23. | If an account exists with that email, we've sent a password reset link. Please follow the instructions to choose a new password. | Se existir uma conta com esse e-mail, enviamos um link de redefinição de senha. Siga as instruções para escolher uma nova senha. |
| 24. | In development, the reset email is printed to the console. | Em desenvolvimento, o e-mail de redefinição é impresso no console. |
| 25. | Reset your password | Redefinir sua senha |
| 26. | Enter the email address associated with your account. | Insira o endereço de e-mail associado à sua conta. |
| 27. | Create your account | Crie sua conta |
| 28. | Sign up to start creating surveys and collecting responses. | Cadastre-se para começar a criar pesquisas e coletar respostas. |
| 29. | Account Type | Tipo de Conta |
| 30. | Organisation Account | Conta de Organização |
| 31. | Create account | Criar conta |
| 32. | Already have an account? | Já tem uma conta? |

---

## Categoria 2: Gerenciamento de Pesquisas (91 Strings)

| # | String em Inglês (English String) | Tradução em Português (Portuguese Translation) |
| :--- | :--- | :--- |
| 1. | This application is in development currently and should NOT be used for live surveys at the moment. | Este aplicativo está atualmente em desenvolvimento e **NÃO** deve ser usado para pesquisas ativas no momento. |
| 2. | Surveys for health care | Pesquisas para cuidados de saúde |
| 3. | Go to Surveys | Ir para Pesquisas |
| 4. | Drag-and-drop groups and questions, apply DaisyUI themes per survey, and control access with roles. | Arraste e solte grupos e perguntas, aplique temas DaisyUI por pesquisa e controle o acesso com funções. |
| 5. | Create a survey | Criar uma pesquisa |
| 6. | Invite your team, scope visibility by organisation and survey membership, and manage participation securely. | Convide sua equipe, defina o escopo da visibilidade por organização e participação na pesquisa e gerencie a participação com segurança. |
| 7. | Manage surveys | Gerenciar pesquisas |
| 8. | Monitor dashboards, export CSV, and audit changes. Everything runs on a secure SSR stack. | Monitore painéis, exporte CSV e audite alterações. Tudo roda em uma pilha SSR segura. |
| 9. | View dashboards | Visualizar painéis |
| 10. | Organisation created. You are now an organisation admin and can host surveys and build a team. | Organização criada. Agora você é um administrador de organização e pode hospedar pesquisas e construir uma equipe. |
| 11. | Question Group Builder | Construtor de Grupos de Perguntas |
| 12. | Survey Dashboard | Painel da Pesquisa |
| 13. | All Questions | Todas as Perguntas |
| 14. | Groups | Grupos |
| 15. | Create and manage groups, then add questions inside each group. | Crie e gerencie grupos e adicione perguntas dentro de cada grupo. |
| 16. | Open a group | Abrir um grupo |
| 17. | Import questions | Importar perguntas |
| 18. | Overwrite survey questions? | Sobrescrever perguntas da pesquisa? |
| 19. | Groups and questions are assigned unique IDs as you edit. Use these IDs to reason about branching later. | Grupos e perguntas recebem IDs exclusivos à medida que você edita. Use esses IDs para raciocinar sobre ramificações mais tarde. |
| 20. | Start typing (or use the sample markdown) to see the survey structure. | Comece a digitar (ou use o markdown de exemplo) para ver a estrutura da pesquisa. |
| 21. | `# Group Title`, followed by a line for the group description | `# Título do Grupo`, seguido por uma linha para a descrição do grupo |
| 22. | `## Question Title`, followed by a line for the question description | `## Título da Pergunta`, seguido por uma linha para a descrição da pergunta |
| 23. | Optional: Required questions | Opcional: Perguntas obrigatórias |
| 24. | Mark a question as required by adding an asterisk `*` | Marque uma pergunta como obrigatória adicionando um asterisco `*` |
| 25. | Required questions must be answered before the form can be submitted | As perguntas obrigatórias devem ser respondidas antes que o formulário possa ser enviado |
| 26. | Place the asterisk immediately after the question title text | Coloque o asterisco imediatamente após o texto do título da pergunta |
| 27. | Works with all question types | Funciona com todos os tipos de perguntas |
| 28. | Optional: Collections with REPEAT | Opcional: Coleções com REPETIR |
| 29. | To mark a group as repeatable, add a line with **REPEAT** (or **REPEAT-5** to cap it) immediately above the group heading. | Para marcar um grupo como repetível, adicione uma linha com **REPETIR** (ou **REPETIR-5** para limitar) imediatamente acima do título do grupo. |
| 30. | To define a child collection nested under a repeatable parent, indent with `>` and add **REPEAT** above the child group: | Para definir uma coleção filha aninhada sob um pai repetível, use o recuo com `>` e adicione **REPETIR** acima do grupo filho: |
| 31. | Use `>` before REPEAT and the group heading to indicate one level of nesting. | Use `>` antes de REPETIR e do título do grupo para indicar um nível de aninhamento. |
| 32. | Groups without REPEAT are normal, non-collection groups. | Grupos sem REPETIR são grupos normais, não coleções. |
| 33. | Optional: Questions with conditional branching | Opcional: Perguntas com ramificação condicional |
| 34. | Branching rules must start with `? when` and reference a question or group ID in curly braces. | As regras de ramificação devem começar com `? when` e fazer referência a uma pergunta ou ID de grupo entre chaves. |
| 35. | Operators: `equals`, `not_equals`, `contains`, `not_contains`, `greater_than`, `less_than`. | Operadores: `equals` (igual a), `not_equals` (diferente de), `contains` (contém), `not_contains` (não contém), `greater_than` (maior que), `less_than` (menor que). |
| 36. | Create Survey | Criar Pesquisa |
| 37. | Create a new survey | Criar uma nova pesquisa |
| 38. | Name | Nome |
| 39. | Description | Descrição |
| 40. | If left blank, a slug will be generated from the name. | Se deixado em branco, um slug (nome amigável para URL) será gerado a partir do nome. |
| 41. | I confirm no **patient-identifiable data** is collected in this survey | Confirmo que **nenhum dado de identificação do paciente** é coletado nesta pesquisa |
| 42. | Keep track of survey status, number of responses and control styling. | Acompanhe o status da pesquisa, número de respostas e controle o estilo. |
| 43. | Draft: build only · Published: accept submissions · Closed: stop submissions | Rascunho: apenas construir · Publicado: aceita envios · Fechado: interrompe envios |
| 44. | Status | Status |
| 45. | Total responses | Total de respostas |
| 46. | No submissions yet | Nenhum envio ainda |
| 47. | Survey style | Estilo da pesquisa |
| 48. | Max responses | Máximo de respostas |
| 49. | Require CAPTCHA for anonymous submissions | Requerer CAPTCHA para envios anônimos |
| 50. | Publish settings | Configurações de publicação |
| 51. | Save publish settings | Salvar configurações de publicação |
| 52. | Once deleted, all data, responses, groups, and permissions will be permanently removed. This action cannot be undone. | Uma vez excluídos, todos os dados, respostas, grupos e permissões serão permanentemente removidos. Esta ação não pode ser desfeita. |
| 53. | Delete this survey | Excluir esta pesquisa |
| 54. | You are about to permanently delete the survey: | Você está prestes a excluir permanentemente a pesquisa: |
| 55. | Deleting this survey will permanently remove: | A exclusão desta pesquisa removerá permanentemente: |
| 56. | All survey data and responses | Todos os dados e respostas da pesquisa |
| 57. | All associated groups and questions | Todos os grupos e perguntas associadas |
| 58. | All collection and publication records | Todos os registros de coleta e publicação |
| 59. | All access permissions and tokens | Todas as permissões de acesso e tokens |
| 60. | To confirm deletion, please type the survey name exactly as shown above: | Para confirmar a exclusão, digite o nome da pesquisa exatamente como mostrado acima: |
| 61. | Type survey name here | Digite o nome da pesquisa aqui |
| 62. | You must type the survey name to confirm deletion. | Você deve digitar o nome da pesquisa para confirmar a exclusão. |
| 63. | Delete Survey Permanently | Excluir Pesquisa Permanentemente |
| 64. | Manage Questions | Gerenciar Perguntas |
| 65. | Question Groups | Grupos de Perguntas |
| 66. | Question Group | Grupo de Perguntas |
| 67. | Questions in this group | Perguntas neste grupo |
| 68. | No questions in this group yet. | Nenhuma pergunta neste grupo ainda. |
| 69. | Question Groups are reusable sets of questions. Arrange them here to control the order in which participants see them. | Grupos de perguntas são conjuntos reutilizáveis de perguntas. Organize-os aqui para controlar a ordem em que os participantes os veem. |
| 70. | Tip: Select groups by clicking their row or checkbox, then click 'Create repeat' to set a name. Selected groups become part of the repeat. | Dica: Selecione grupos clicando em sua linha ou caixa de seleção e, em seguida, clique em 'Criar repetição' para definir um nome. Os grupos selecionados se tornam parte da repetição. |
| 71. | Selected for repeat | Selecionado para repetição |
| 72. | Remove this group from its repeat? | Remover este grupo de sua repetição? |
| 73. | Delete this group? | Excluir este grupo? |
| 74. | Delete | Excluir |
| 75. | No groups yet. Create one to get started. | Nenhum grupo ainda. Crie um para começar. |
| 76. | Create repeat from selection | Criar repetição a partir da seleção |
| 77. | selected | selecionado |
| 78. | Back to dashboard | Voltar para o painel |
| 79. | Create new question group | Criar novo grupo de perguntas |
| 80. | New group name | Novo nome do grupo |
| 81. | Create | Criar |
| 82. | Cancel | Cancelar |
| 83. | No surveys yet. | Nenhuma pesquisa ainda. |
| 84. | Survey users | Usuários da pesquisa |
| 85. | Back to survey | Voltar para a pesquisa |
| 86. | Your response has been recorded. | Sua resposta foi registrada. |
| 87. | Unlock Survey | Desbloquear Pesquisa |
| 88. | Survey key | Chave da pesquisa |
| 89. | Enter the one-time survey key to decrypt sensitive fields for this session. | Insira a chave da pesquisa de uso único para descriptografar campos sensíveis para esta sessão. |
| 90. | Unlock | Desbloquear |
| 91. | Invite Tokens | Tokens de Convite |
| 92. | Invite tokens | Tokens de convite |
| 93. | Token | Token |
| 94. | Created | Criado |
| 95. | No tokens yet. | Nenhum token ainda. |
| 96. | Manage invite tokens | Gerenciar tokens de convite |
| 97. | Invite token | Token de convite |
| 98. | Add user to survey | Adicionar usuário à pesquisa |
| 99. | No surveys yet | Nenhuma pesquisa ainda |
| 100. | Survey slug | Slug da pesquisa |
| 101. | Users by survey | Usuários por pesquisa |

---

## Categoria 3: Elementos de Formulário e Validação (23 Strings)

| # | String em Inglês (English String) | Tradução em Português (Portuguese Translation) |
| :--- | :--- | :--- |
| 1. | Choose your preferred language. This affects all text in the application. | Escolha seu idioma preferido. Isso afeta todo o texto no aplicativo. |
| 2. | Choose your theme. This only affects your view and is saved in your browser. | Escolha seu tema. Isso afeta apenas sua visualização e é salvo no seu navegador. |
| 3. | URL Name or 'Slug' (optional) | Nome da URL ou 'Slug' (opcional) |
| 4. | Optional: Follow-up text inputs | Opcional: Entradas de texto de acompanhamento |
| 5. | Add a follow-up text input to any option by adding an indented line starting with + | Adicione uma entrada de texto de acompanhamento a qualquer opção adicionando uma linha recuada começando com + |
| 6. | The text after + becomes the label for the follow-up input field | O texto após + se torna o rótulo para o campo de entrada de acompanhamento |
| 7. | Follow-up lines must start with + and be indented (at least 2 spaces) | As linhas de acompanhamento devem começar com + e ser recuadas (pelo menos 2 espaços) |
| 8. | For Likert scales, provide min/max and optional labels | Para escalas Likert, forneça min/max e rótulos opcionais |
| 9. | select menu | menu de seleção |
| 10. | (optional) | (opcional) |
| 11. | Create repeat | Criar repetição |
| 12. | Nest under existing (optional) | Aninhar sob existente (opcional) |
| 13. | Nesting is limited to one level (Parent → Child) by design. | O aninhamento é limitado a um nível (Pai → Filho) por design. |
| 14. | Note: In the preview below, a repeat card will only show if there is at least one group marked as repeatable in this survey. You can test adding/removing instances. | Nota: Na pré-visualização abaixo, um cartão de repetição só será exibido se houver pelo menos um grupo marcado como repetível nesta pesquisa. Você pode testar a adição/remoção de instâncias. |
| 15. | Importing from Markdown will delete all existing question groups, questions, branching rules, and repeats. This action cannot be undone. | A importação de Markdown excluirá todos os grupos de perguntas, perguntas, regras de ramificação e repetições existentes. Esta ação não pode ser desfeita. |
| 16. | Optional: Follow-up text inputs (dropdown, mc_single, mc_multi, yesno) | Opcional: Entradas de texto de acompanhamento (dropdown, mc_single, mc_multi, yesno) |
| 17. | For yesno, provide exactly 2 options (Yes/No) with optional follow-ups | Para sim/não, forneça exatamente 2 opções (Sim/Não) com acompanhamentos opcionais |
| 18. | Operators mirror the survey builder: equals, not_equals, contains, not_contains, greater_than, less_than | Os operadores espelham o construtor de pesquisas: equals, not_equals, contains, not_contains, greater_than, less_than |
| 19. | Point to a group ID to jump to that group, or a question ID to jump directly to that question | Aponte para um ID de grupo para pular para esse grupo, ou para um ID de pergunta para pular diretamente para essa pergunta |
| 20. | Assign stable IDs by placing them in curly braces at the end of group or question titles | Atribua IDs estáveis colocando-os entre chaves no final dos títulos de grupo ou pergunta |
| 21. | IDs are normalised to lowercase slugs; keep them unique within your document. | Os IDs são normalizados para slugs em minúsculo; mantenha-os exclusivos dentro do seu documento. |
| 22. | If the type requires options, list each on a line starting with - | Se o tipo requer opções, liste cada uma em uma linha começando com - |
| 23. | (type) on the next line in parentheses | (tipo) na próxima linha entre parênteses |

---

## Categoria 4: Componentes de UI e Navegação (16 Strings)

| # | String em Inglês (English String) | Tradução em Português (Portuguese Translation) |
| :--- | :--- | :--- |
| 1. | Organisation created. You are an organisation admin. | Organização criada. Você é um administrador de organização. |
| 2. | Analyze | Analisar |
| 3. | Census | Censo/Recenseamento |
| 4. | Home | Início |
| 5. | Distribute | Distribuir |
| 6. | Explore docs | Explorar documentos |
| 7. | See capabilities | Ver capacidades |
| 8. | Live structure preview | Pré-visualização da estrutura ao vivo |
| 9. | Preview (read-only) | Pré-visualização (somente leitura) |
| 10. | Public link | Link público |
| 11. | Unlisted link | Link não listado |
| 12. | Preview | Pré-visualizar |
| 13. | Request a new link | Solicitar um novo link |
| 14. | Send reset link | Enviar link de redefinição |
| 15. | Create an organisation to collaborate with a team | Crie uma organização para colaborar com uma equipe |
| 16. | Create surveys and manage your own responses | Crie pesquisas e gerencie suas próprias respostas |

---

## Categoria 5: Documentação e Texto de Ajuda (8 Strings)

| # | String em Inglês (English String) | Tradução em Português (Portuguese Translation) |
| :--- | :--- | :--- |
| 1. | **REPEAT** = unlimited repeats. **REPEAT-1** means only 1 allowed, **REPEAT-1-5** allows 1 to 5. | **REPETIR** = repetições ilimitadas. **REPETIR-1** significa apenas 1 permitido, **REPETIR-1-5** permite de 1 a 5. |
| 2. | Not all options need follow-ups—only add them where needed | Nem todas as opções precisam de acompanhamentos—adicione-os apenas onde necessário |
| 3. | **Groups** are reusable sets of questions. You can mark one or more groups as a **repeat** (collection), allowing users to add multiple instances of those groups when filling out the survey. | **Grupos** são conjuntos reutilizáveis de perguntas. Você pode marcar um ou mais grupos como uma **repetição** (coleção), permitindo que os usuários adicionem múltiplas instâncias desses grupos ao preencherem a pesquisa. |
| 4. | Use markdown with the following structure: | Use markdown com a seguinte estrutura: |
| 5. | Supported types | Tipos suportados |
| 6. | categories listed with - | categorias listadas com - |
| 7. | Organisation names don't need to be unique. Multiple organisations can have the same name—you'll only see and manage your own. | Os nomes de organização não precisam ser exclusivos. Múltiplas organizações podem ter o mesmo nome—você verá e gerenciará apenas a sua. |
| 8. | Format reference | Referência de formato |

---

## Categoria 6: Texto Geral da UI (89 Strings)

| # | String em Inglês (English String) | Tradução em Português (Portuguese Translation) |
| :--- | :--- | :--- |
| 1. | Your Profile | Seu Perfil |
| 2. | Your badges | Seus emblemas |
| 3. | Language preference updated successfully. | Preferência de idioma atualizada com sucesso. |
| 4. | There was an error updating your language preference. | Ocorreu um erro ao atualizar sua preferência de idioma. |
| 5. | Project theme saved. | Tema do projeto salvo. |
| 6. | You have staff-level access to the platform | Você tem acesso de nível de equipe à plataforma |
| 7. | You have full administrative access to the platform | Você tem acesso administrativo total à plataforma |
| 8. | Appearance | Aparência |
| 9. | Language | Idioma |
| 10. | Save Language Preference | Salvar Preferência de Idioma |
| 11. | Theme | Tema |
| 12. | Light | Claro |
| 13. | Dark | Escuro |
| 14. | Enable JavaScript to change theme. | Habilite o JavaScript para alterar o tema. |
| 15. | Window | Janela |
| 16. | Today | Hoje |
| 17. | Last 7 days | Últimos 7 dias |
| 18. | Last 14 days | Últimos 14 dias |
| 19. | Closed | Fechado |
| 20. | Authenticated | Autenticado |
| 21. | Public | Público |
| 22. | Unlisted | Não listado |
| 23. | Start at | Começa em |
| 24. | End at | Termina em |
| 25. | Danger Zone | Zona de Perigo |
| 26. | Warning: This action cannot be undone! | Aviso: Esta ação não pode ser desfeita! |
| 27. | Yes | Sim |
| 28. | No | Não |
| 29. | Professional details | Detalhes profissionais |
| 30. | Submit | Enviar |
| 31. | Repeats | Repetições |
| 32. | Remove repeat | Remover repetição |
| 33. | Clear | Limpar |
| 34. | Help | Ajuda |
| 35. | Repeat name | Nome da repetição |
| 36. | Minimum items | Itens mínimos |
| 37. | Maximum items | Itens máximos |
| 38. | Unlimited | Ilimitado |
| 39. | Nesting is limited to one level. | O aninhamento é limitado a um nível. |
| 40. | Import | Importar |
| 41. | Organisation users | Usuários da organização |
| 42. | How many | Quantos |
| 43. | Expires at (ISO) | Expira em (ISO) |
| 44. | Generate | Gerar |
| 45. | Export CSV | Exportar CSV |
| 46. | Expires | Expira |
| 47. | Used | Usado |
| 48. | Used by | Usado por |
| 49. | User management | Gerenciamento de usuários |
| 50. | You don't have an organisation to manage yet. | Você ainda não tem uma organização para gerenciar. |
| 51. | Organisation | Organização |
| 52. | Add user to org | Adicionar usuário à org |
| 53. | No users yet | Nenhum usuário ainda |
| 54. | No members | Nenhum membro |
| 55. | Please correct the error below. | Por favor, corrija o erro abaixo. |
| 56. | Built by | Construído por |
| 57. | GitHub | GitHub |
| 58. | Issues | Problemas |
| 59. | Releases | Lançamentos |
| 60. | Contributing | Contribuir |
| 61. | Version | Versão |
| 62. | Branch | Branch |
| 63. | Commit | Commit |
| 64. | Individual User | Usuário Individual |
| 65. | Organisation Name | Nome da Organização |
| 66. | e.g. Acme Health Research | ex. Acme Pesquisa em Saúde |
| 67. | Leave blank to use default name | Deixe em branco para usar o nome padrão |
| 68. | Note: | Nota: |
| 69. | Markdown | Markdown |
| 70. | Add `class="required"` to mark a question as required | Adicione `class="required"` para marcar uma pergunta como obrigatória |
| 71. | The asterisk `*` method is recommended for simplicity | O método do asterisco `*` é recomendado por simplicidade |
| 72. | free text | texto livre |
| 73. | numeric input | entrada numérica |
| 74. | multiple choice (single) | múltipla escolha (única) |
| 75. | multiple choice (multi) | múltipla escolha (múltipla) |
| 76. | orderable list | lista ordenável |
| 77. | image choice | escolha de imagem |
| 78. | yes/no | sim/não |
| 79. | Draft | Rascunho |
| 80. | Published | Publicado |
| 81. | For options that should have follow-up text input, add an indented line starting with + followed by the label text | Para opções que devem ter entrada de texto de acompanhamento, adicione uma linha recuada começando com + seguida pelo texto do rótulo |
| 82. | Works with mc_single, mc_multi, dropdown, and yesno question types | Funciona com os tipos de pergunta mc_single, mc_multi, dropdown e yesno |
| 83. | Published: ready to accept responses. | Publicado: pronto para aceitar respostas. |
| 84. | Open the survey in a new window to invite participants. | Abra a pesquisa em uma nova janela para convidar participantes. |
| 85. | What's this? | O que é isso? |
| 86. | Visibility | Visibilidade |
| 87. | Authenticated: participants must log in before accessing. Public: anyone with the link. Unlisted: secret link, no directory listing. | Autenticado: os participantes devem fazer login antes de acessar. Público: qualquer pessoa com o link. Não listado: link secreto, sem listagem em diretório. |
| 88. | For public/unlisted surveys, all form fields (name, email, etc.) are automatically encrypted—unless you explicitly opt out of encryption for a given question. The survey will prompt for a one-time decryption key on dashboard load. | Para pesquisas públicas/não listadas, todos os campos do formulário (nome, e-mail, etc.) são automaticamente criptografados—a menos que você desative explicitamente a criptografia para uma determinada pergunta. A pesquisa solicitará uma chave de descriptografia de uso único ao carregar o painel. |
| 89. | Submissions | Envios |
