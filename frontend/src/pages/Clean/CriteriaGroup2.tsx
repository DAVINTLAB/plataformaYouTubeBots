interface CriteriaGroup2Props {
  selected: Set<string>;
  onToggle: (criteria: string) => void;
  thresholdChars: number;
  thresholdSeconds: number;
  onThresholdCharsChange: (v: number) => void;
  onThresholdSecondsChange: (v: number) => void;
}

const CRITERIA = [
  {
    id: "curtos",
    label: "Comentários curtos/repetitivos",
    description: "Usuários com maioria de comentários curtos ou com alto índice de repetição.",
  },
  {
    id: "intervalo",
    label: "Intervalo temporal (rajada)",
    description: "Usuários que postaram comentários consecutivos em intervalo muito curto.",
  },
  {
    id: "identicos",
    label: "Idênticos em múltiplos vídeos",
    description: "Usuários que postaram comentários iguais em coletas diferentes no banco.",
  },
  {
    id: "perfil",
    label: "Perfil suspeito",
    description:
      "Sem foto de avatar ou canal criado recentemente (<90 dias) — usa dados já coletados.",
  },
];

export function CriteriaGroup2({
  selected,
  onToggle,
  thresholdChars,
  thresholdSeconds,
  onThresholdCharsChange,
  onThresholdSecondsChange,
}: CriteriaGroup2Props) {
  return (
    <div>
      <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
        Grupo 2 — Critérios comportamentais
      </h3>
      <div className="flex flex-col gap-2">
        {CRITERIA.map((c) => (
          <div key={c.id}>
            <label className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:border-davint-400 transition-colors cursor-pointer">
              <input
                type="checkbox"
                checked={selected.has(c.id)}
                onChange={() => onToggle(c.id)}
                className="mt-0.5 accent-davint-400"
              />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-700">{c.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{c.description}</p>
              </div>
            </label>

            {/* Threshold inputs */}
            {c.id === "curtos" && selected.has("curtos") && (
              <div className="ml-9 mt-2 mb-1">
                <label className="form-group">
                  <span className="form-label">Mínimo de caracteres</span>
                  <input
                    type="number"
                    className="form-input w-32"
                    min={1}
                    max={500}
                    value={thresholdChars}
                    onChange={(e) => onThresholdCharsChange(Number(e.target.value))}
                  />
                </label>
              </div>
            )}

            {c.id === "intervalo" && selected.has("intervalo") && (
              <div className="ml-9 mt-2 mb-1">
                <label className="form-group">
                  <span className="form-label">Intervalo máximo (segundos)</span>
                  <input
                    type="number"
                    className="form-input w-32"
                    min={1}
                    max={3600}
                    value={thresholdSeconds}
                    onChange={(e) => onThresholdSecondsChange(Number(e.target.value))}
                  />
                </label>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
