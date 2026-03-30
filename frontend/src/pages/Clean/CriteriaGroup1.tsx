interface CriteriaGroup1Props {
  selected: Set<string>;
  onToggle: (criteria: string) => void;
}

const CRITERIA = [
  {
    id: "percentil",
    label: "Percentil (top 30%)",
    description: "Seleciona usuários com número de comentários no top 30% do vídeo.",
  },
  {
    id: "media",
    label: "Acima da média",
    description:
      "Seleciona usuários com número de comentários acima da média (após remoção de outliers via IQR).",
  },
  {
    id: "moda",
    label: "Acima da moda",
    description:
      "Seleciona usuários com número de comentários acima da moda (após remoção de outliers via IQR).",
  },
  {
    id: "mediana",
    label: "Acima da mediana",
    description:
      "Seleciona usuários com número de comentários acima da mediana (após remoção de outliers via IQR).",
  },
];

export function CriteriaGroup1({ selected, onToggle }: CriteriaGroup1Props) {
  return (
    <div>
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
        Grupo 1 — Critérios estatísticos de volume
      </h3>
      <div className="flex flex-col gap-2">
        {CRITERIA.map((c) => (
          <label
            key={c.id}
            className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:border-davint-400 transition-colors cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.has(c.id)}
              onChange={() => onToggle(c.id)}
              className="mt-0.5 accent-davint-400"
            />
            <div>
              <p className="text-sm font-medium text-gray-700">{c.label}</p>
              <p className="text-xs text-gray-500 mt-0.5">{c.description}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
