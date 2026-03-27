# Padrões de Frontend

## Arquitetura

```
pages/       → telas por US — compõem componentes e consomem hooks
components/  → responsabilidade visual apenas (SRP)
hooks/       → lógica de negócio isolada (useAnnotation, useClean, useDashboard, etc.)
api/         → chamadas ao backend — única camada que faz fetch (DIP)
```

Componentes nunca fazem `fetch` diretamente — sempre via hooks que consomem `api/`.

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

## Regras de segurança

- Token JWT em `sessionStorage` (persiste o refresh, some ao fechar a aba) — nunca em `localStorage`
- Campos de API key sempre com `type="password"` e `autoComplete="off"`
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