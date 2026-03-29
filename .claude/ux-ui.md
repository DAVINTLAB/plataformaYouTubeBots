# Padrões de UX/UI

## Heurísticas de Nielsen aplicadas

### 1. Visibilidade do status do sistema

- Sempre informar o que está acontecendo: spinners durante carregamento, contadores ao vivo durante coleta, badges de status nas listas
- StatusBadge com cores semânticas: azul (em andamento), roxo (enriquecendo), verde (concluído), vermelho (falhou), laranja (restrito)
- Progresso por fase: "Coletando comentários...", "Buscando respostas...", "Obtendo dados dos autores..."

### 2. Correspondência entre o sistema e o mundo real

- Linguagem em português, sem jargão técnico nas mensagens ao usuário
- Termos do domínio da pesquisa: "coleta", "anotação", "conflito", "dataset", "pesquisador"
- IDs de US (US-01, US-02) são internos — nunca exibidos na interface

### 3. Controle e liberdade do usuário

- Coleta retomável: se navegar para outra tela, pode voltar e continuar
- `window.confirm` antes de ações destrutivas (deletar coleta)
- Botão "Nova Coleta" sempre acessível após conclusão
- Card de interrupção com instruções claras de como retomar

### 4. Consistência e padrões

- Layout `max-w-6xl` em todas as páginas — otimizado para 1080p
- Container padrão: `<main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">`
- PageHeader em toda página autenticada (logo, breadcrumb, usuário)
- StepsCard para instruções em todas as páginas de etapa
- Tabelas com colunas consistentes: dados à esquerda, ações à direita, destrutivas isoladas

### 5. Prevenção de erros

- Botões desabilitados quando campos obrigatórios estão vazios
- Validação de JSON no frontend antes de enviar ao backend
- API key como `type="password"` com `autoComplete="new-password"`
- Coletas em andamento não podem ser deletadas (HTTP 409)

### 6. Reconhecimento em vez de memorização

- Cards da HomePage mostram todas as etapas do pipeline — inclusive restritas (cinza com badge)
- Pesquisador sabe que "Revisar Conflitos" existe sem precisar ser admin
- Formato de import documentado com exemplo colapsável (`<details>`)

### 7. Flexibilidade e eficiência de uso

- Tabs "Coletar via API" / "Importar JSON" para fluxos diferentes
- Export em JSON (reimportável) e CSV (análise em Excel/Pandas)
- Campo de vídeo aceita ID puro ou URL completa do YouTube

### 8. Design estético e minimalista

- Cards com espaço em branco generoso, sem sobrecarga visual
- Informações secundárias em texto menor e cor mais clara
- Ícones SVG inline, sem dependência de biblioteca de ícones
- Grid 3+2 centrado na HomePage — equilibrado visualmente

### 9. Ajudar usuários a reconhecer, diagnosticar e recuperar erros

- Mensagens de erro descritivas em português (nunca "Erro inesperado" genérico)
- Erros da YouTube API traduzidos: "API key inválida", "Quota esgotada", "Vídeo privado"
- Erros internos incluem tipo e mensagem da exceção para diagnóstico
- Banner amarelo para estados interrompidos com instruções de recuperação

### 10. Ajuda e documentação

- StepsCard com passo a passo em cada etapa
- Card de formato de import com exemplo JSON colapsável
- Notas explicativas em texto cinza abaixo de campos sensíveis (API key)

## Regras de UI

### Cores semânticas

| Contexto | Cor |
|---|---|
| Ação primária | `bg-davint-400` (roxo da marca) |
| Em andamento (coleta) | `text-blue-700`, `bg-blue-50` |
| Sucesso | `text-green-600`, `bg-green-50` |
| Aviso / interrupção | `text-yellow-700`, `bg-yellow-50` |
| Erro / destrutivo | `text-red-600`, `bg-red-50` |
| Restrito | `text-orange-600`, `bg-orange-50` |
| Enriquecimento | `text-purple-700`, `bg-purple-50` |
| Informativo | `text-davint-600`, `bg-davint-50` |
| Aguardando | `text-yellow-700`, `bg-yellow-50` |
| Neutro / desabilitado | `text-gray-400`, `bg-gray-100` |

### Tabelas

- Cabeçalhos: `text-[11px] font-bold uppercase tracking-wider text-gray-400`
- Colunas de dados: alinhadas à esquerda
- Coluna de export: botões de texto (`text-davint-400`)
- Coluna de ação destrutiva: isolada à direita, só ícone, `text-red-400` com hover `text-red-600`
- Sem header na coluna destrutiva — ação perigosa não deve ser convidativa

### Botões

| Tipo | Classe | Uso |
|---|---|---|
| Primário | `btn btn-primary` | Ação principal do formulário |
| Ghost | `btn btn-ghost` | Ação secundária (Nova Coleta, Tentar novamente) |
| Danger | `btn btn-danger` | Ação destrutiva com confirmação |
| Link / texto | `text-xs font-medium text-davint-400 hover:underline` | Ações inline em tabelas |

### Cards da HomePage

- Grid: `flex flex-wrap justify-center gap-4` — layout 3+2 com segunda linha centrada
- Cards de mesma altura via wrapper `flex` + Card `w-full`
- Etapas admin-only: visíveis para todos com badge "Restrito a admins" (laranja), sem interação para anotadores
- Saudação usa nome do pesquisador (`user.name`), não username

### Responsividade

- Target principal: monitores 1080p (1920×1080)
- `max-w-6xl` (1152px) em todas as páginas
- Grid responsivo: 1 coluna mobile → 2 tablet → 3 desktop
