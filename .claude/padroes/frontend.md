# Padrões de Frontend

## Arquitetura

```
pages/       → telas por US — compõem componentes e consomem hooks
components/  → responsabilidade visual apenas (SRP)
hooks/       → lógica de negócio isolada (useAnnotation, useClean, useDashboard, etc.)
api/         → chamadas ao backend — única camada que faz fetch (DIP)
```

Componentes nunca fazem `fetch` diretamente — sempre via hooks que consomem `api/`.

## Layout

- **Largura máxima**: todas as páginas usam `max-w-6xl` (1152px) — otimizado para monitores 1080p
- **Container padrão**: `<main className="flex-1 px-8 py-9 max-w-6xl w-full mx-auto">`
- **Grid de cards na HomePage**: `flex flex-wrap justify-center gap-4` — layout 3+2 com segunda linha centrada
- **Cards de etapas admin-only**: visíveis para todos os usuários, mas com badge "Restrito a admins" (laranja) e sem interação para anotadores — o usuário precisa saber que a etapa existe no pipeline

## SOLID na prática

### SRP — um componente, uma responsabilidade visual

```tsx
// components/AnnotationCard.tsx — só renderiza
export function AnnotationCard({ comment, onLabel }: AnnotationCardProps) { ... }

// hooks/useAnnotation.ts — só lógica
export function useAnnotation(datasetId: string) {
  const [current, setCurrent] = useState<Comment | null>(null)
  const save = async (label: 'bot' | 'humano', justificativa?: string) => { ... }
  return { current, save }
}

// pages/AnnotatePage.tsx — compõe os dois
export function AnnotatePage() {
  const { current, save } = useAnnotation(datasetId)
  return <AnnotationCard comment={current} onLabel={save} />
}
```

### OCP — componentes de gráfico extensíveis via props

```tsx
// components/Chart.tsx — recebe data e layout, nunca hardcoded
interface ChartProps {
  data: Plotly.Data[]
  layout?: Partial<Plotly.Layout>
  title?: string
}

export function Chart({ data, layout, title }: ChartProps) {
  return (
    <Plot
      data={data}
      layout={{ title, autosize: true, ...layout }}
      style={{ width: '100%' }}
      useResizeHandler
    />
  )
}
```

### DIP — api/ é a única camada que conhece o backend

```ts
// api/annotate.ts
const API_URL = import.meta.env.VITE_API_URL

export async function saveAnnotation(payload: AnnotationPayload): Promise<Annotation> {
  const res = await fetch(`${API_URL}/annotate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

// hooks/useAnnotation.ts — consome api/, não faz fetch diretamente
import { saveAnnotation } from '@/api/annotate'
```

## Componentização

### Regra de decisão

| Situação | Onde colocar |
|----------|-------------|
| Elemento visual usado em **2+ páginas distintas** | `components/` |
| Elemento visual exclusivo de uma página, mas com lógica própria | subcomponente em `pages/<US>/` |
| Lógica de negócio reutilizável | `hooks/` |
| Toda a lógica de uma página em um único componente gigante | **Proibido** — extrair subcomponentes |

### Componentes globais existentes (`components/`)

| Componente | Props principais | Uso |
|------------|-----------------|-----|
| `PageHeader` | `breadcrumbs?: BreadcrumbItem[]`, `onChangePassword?: () => void` | Todas as páginas autenticadas — **obrigatório** |
| `StatusBadge` | `status: string`, `size?: "sm"\|"md"` | Badge colorido de status de coleta |
| `ProgressBar` | `percent?: number`, `indeterminate?: boolean`, `label?: string`, `size?: "sm"\|"md"` | Barra de progresso determinada ou com pulso |
| `StepsCard` | `title?: string`, `steps: { label: string; description?: string }[]` | Card de instruções passo a passo — **obrigatório em toda etapa inicial de US** |
| `ProtectedRoute` | — | Rota que exige autenticação |

### PageHeader — uso obrigatório em todas as páginas autenticadas

```tsx
// Página raiz (sem breadcrumb)
<PageHeader onChangePassword={() => setShowChangePassword(true)} />

// Página secundária (com breadcrumb)
<PageHeader
  breadcrumbs={[{ label: "Início", to: "/" }, { label: "Nome da Página" }]}
  onChangePassword={() => setShowChangePassword(true)}   // omitir se não houver modal de senha
/>
```

`PageHeader` gerencia internamente: logo DaVint, navegação, badge de papel, nome completo + username, botão "Sair". A página **não** deve re-implementar nenhum desses elementos.

### StatusBadge

```tsx
// Tamanho padrão — painéis de detalhe
<StatusBadge status={collection.status} />

// Tamanho reduzido — linhas de tabela
<StatusBadge status={col.status} size="sm" />
```

Reconhece os valores `pending`, `running`, `completed`, `failed`. Para outros valores exibe o texto literal com fundo cinza.

### ProgressBar

```tsx
// Progresso determinado (ex: download com Content-Length)
<ProgressBar percent={downloadPercent} label={`${downloadPercent}%`} size="sm" />

// Progresso indeterminado (ex: coleta em andamento)
<ProgressBar indeterminate label="Coletando comentários…" />
```

### Cards de instrução por etapa

Toda página de US deve orientar o usuário em cada etapa do fluxo:

| Etapa | Como instruir |
|-------|--------------|
| **Idle / formulário inicial** | `<StepsCard title="Passo a passo" steps={[...]} />` acima do formulário |
| **Processamento ativo** | Notice inline (ex: `bg-davint-50`) com aviso de aguardar + o que acontece se sair |
| **Estado interrompido / retomada** | Banner amarelo (`bg-yellow-50`) explicando o que ocorreu, quantos itens foram preservados e como retomar |
| **Concluído** | CTA claro para o próximo passo do fluxo (ex: "Ir para Limpeza →") |
| **Falha** | Mensagem de erro + botão "Tentar novamente" |

```tsx
// Exemplo — etapa idle
<StepsCard
  title="Passo a passo"
  steps={[
    { label: "Passo 1", description: "Descrição curta." },
    { label: "Passo 2", description: "Descrição curta." },
  ]}
/>

// Exemplo — processamento ativo
<div className="flex items-start gap-2 p-3 bg-davint-50 rounded-lg mb-4">
  {/* ícone info */}
  <p className="text-xs text-davint-700">Aguarde nesta página…</p>
</div>

// Exemplo — interrompido
<div className="flex items-start gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
  {/* ícone aviso */}
  <div>
    <p className="text-sm font-semibold text-yellow-800">Interrompido</p>
    <p className="text-xs text-yellow-700 mt-1">Explicação do que ocorreu e como retomar.</p>
  </div>
</div>
```

### Tabs de criação/import — obrigatório em toda US com import

Toda página de US que permite importar dados deve ter **duas abas** no topo do conteúdo, separando os fluxos:

```tsx
<div className="flex gap-1 mb-4 border-b border-gray-200">
  <button
    className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
      tab === "create"
        ? "border-davint-400 text-davint-500"
        : "border-transparent text-gray-500 hover:text-gray-700"
    }`}
    onClick={() => setTab("create")}
  >
    Criar via ...
  </button>
  <button
    className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
      tab === "import"
        ? "border-davint-400 text-davint-500"
        : "border-transparent text-gray-500 hover:text-gray-700"
    }`}
    onClick={() => setTab("import")}
  >
    Importar JSON
  </button>
</div>
```

- O import aceita o **mesmo formato JSON** gerado pelo export — simetria total
- A aba de import inclui card explicativo com formato esperado (`bg-davint-50`)
- Mensagens de erro/sucesso ficam **acima** das tabs (compartilhadas entre os fluxos)
- A tabela de itens existentes fica **abaixo** das tabs (visível em ambas)

### O que NÃO deve ser repetido inline

- Header `<header>` — sempre usar `<PageHeader>`
- Badge de status de coleta — sempre usar `<StatusBadge>`
- Barra de progresso — sempre usar `<ProgressBar>`
- Constantes `ROLE_LABEL`, `STATUS_LABEL`, `STATUS_COLOR` — vivem dentro dos componentes, não nas páginas

### Adicionando um novo componente global

1. Criar em `components/NomeDoComponente.tsx`
2. Documentar na tabela acima no `frontend.md`
3. Atualizar o `CLAUDE.md` na seção de componentização

## CSS (Tailwind CSS v3)

O projeto usa **Tailwind CSS v3** com PostCSS. Não há CSS Modules nem outros frameworks CSS.

```
src/index.css           → @tailwind directives + @layer components (classes reutilizáveis)
tailwind.config.js      → content paths, cores DaVint, animações customizadas
```

### Cores do tema (tailwind.config.js)

```js
colors: {
  davint: {
    50:  '#edf7fa',
    400: '#38b5c9',  // primária — botões, foco, badges
    500: '#2ea0b1',  // hover
  }
}
```

### Classes utilitárias globais (@layer components em index.css)

Usadas diretamente no JSX (sem import):

| Classe | Uso |
|--------|-----|
| `.btn .btn-primary` | botão primário (teal DaVint) |
| `.btn .btn-danger` | botão destrutivo (vermelho, outline) |
| `.btn .btn-ghost` | botão secundário (outline cinza) |
| `.btn .btn-full` | botão largura total |
| `.form-group / .form-label / .form-input` | campos de formulário |
| `.badge .badge-admin` | badge papel admin (teal) |
| `.badge .badge-user` | badge papel pesquisador (verde) |
| `.alert .alert-error` | mensagem de erro inline |

### Regra

Layout e estilos de página ficam como classes Tailwind inline no JSX. Classes que aparecem em 3 ou mais componentes distintos sobem para `@layer components` em `index.css`.

## Regras de segurança

- Token JWT em `sessionStorage` (persiste o refresh, some ao fechar a aba) — nunca em `localStorage`
- Campos de API key sempre com `type="password"` e `autoComplete="new-password"` (browsers modernos ignoram `"off"` — `"new-password"` impede o gerenciador de senhas de propor salvar)
- Redirecionar para `/login` automaticamente em resposta 401
- Variáveis de ambiente sempre via `import.meta.env.VITE_*` — nunca hardcoded

## Validação de formulários

```tsx
// campo justificativa obrigatório ao selecionar bot
const isValid = label !== 'bot' || justificativa.trim().length > 0

<button disabled={!isValid} onClick={handleSubmit}>
  Salvar
</button>
```

## Convenções

- Componentes em PascalCase, hooks com prefixo `use`
- Props tipadas com `interface`, nunca `any`
- Hooks customizados retornam objeto nomeado (`{ data, loading, error }`)
- Erros de API exibidos ao usuário — nunca silenciosos

## Plotly.js

```tsx
import Plot from 'react-plotly.js'

// sempre com useResizeHandler e width 100% para responsividade
<Plot
  data={data}
  layout={{ autosize: true }}
  style={{ width: '100%' }}
  useResizeHandler
/>
```