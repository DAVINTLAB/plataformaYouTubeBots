interface KpiCard {
  label: string;
  value: number | string;
  color?: string;
}

interface KpiCardsProps {
  cards: KpiCard[];
}

const STYLES: Record<string, { bg: string; text: string; ring: string }> = {
  green: { bg: "bg-emerald-50", text: "text-emerald-600", ring: "ring-emerald-200" },
  red: { bg: "bg-red-50", text: "text-red-600", ring: "ring-red-200" },
  yellow: { bg: "bg-amber-50", text: "text-amber-600", ring: "ring-amber-200" },
  blue: { bg: "bg-blue-50", text: "text-blue-600", ring: "ring-blue-200" },
  orange: { bg: "bg-orange-50", text: "text-orange-600", ring: "ring-orange-200" },
  neutral: { bg: "bg-gray-50", text: "text-gray-700", ring: "ring-gray-200" },
};

export function KpiCards({ cards }: KpiCardsProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 mb-6">
      {cards.map((card) => {
        const s = STYLES[card.color ?? "neutral"];
        return (
          <div
            key={card.label}
            className={`rounded-xl ring-1 ${s.ring} ${s.bg} px-3 py-3.5 flex flex-col items-center`}
          >
            <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              {card.label}
            </p>
            <p className={`text-2xl font-bold leading-none ${s.text}`}>{card.value}</p>
          </div>
        );
      })}
    </div>
  );
}
