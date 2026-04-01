interface CriteriaFilterBarProps {
  active: string[];
  onChange: (criteria: string[]) => void;
}

const GROUPS = [
  {
    label: "Numérico",
    criteria: ["percentil", "media", "moda", "mediana"],
  },
  {
    label: "Comportamental",
    criteria: ["curtos", "intervalo", "identicos", "perfil"],
  },
];

export function CriteriaFilterBar({ active, onChange }: CriteriaFilterBarProps) {
  const toggle = (crit: string) => {
    if (active.includes(crit)) {
      onChange(active.filter((c) => c !== crit));
    } else {
      onChange([...active, crit]);
    }
  };

  const clear = () => onChange([]);

  return (
    <div className="flex flex-wrap items-center gap-4 p-3 bg-gray-50 rounded-lg border border-gray-200 mb-4">
      {GROUPS.map((group) => (
        <div key={group.label} className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
            {group.label}:
          </span>
          {group.criteria.map((crit) => (
            <label
              key={crit}
              className="flex items-center gap-1 text-xs text-gray-600 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={active.includes(crit)}
                onChange={() => toggle(crit)}
                className="rounded border-gray-300 text-davint-400 focus:ring-davint-400"
              />
              {crit.charAt(0).toUpperCase() + crit.slice(1)}
            </label>
          ))}
        </div>
      ))}
      {active.length > 0 && (
        <button onClick={clear} className="text-xs text-davint-400 hover:underline ml-auto">
          Limpar filtros
        </button>
      )}
    </div>
  );
}
