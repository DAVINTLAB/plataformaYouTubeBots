interface StepItem {
  label: string;
  description?: string;
}

interface StepsCardProps {
  title?: string;
  steps: StepItem[];
}

export function StepsCard({ title = "Como funciona", steps }: StepsCardProps) {
  return (
    <div className="bg-davint-50 rounded-xl p-5 mb-6">
      <h3 className="text-xs font-bold uppercase tracking-wider text-davint-600 mb-4">{title}</h3>
      <ol className="flex flex-col gap-3">
        {steps.map((step, i) => (
          <li key={i} className="flex gap-3 items-start">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-davint-400 text-white text-[10px] font-bold flex items-center justify-center mt-0.5">
              {i + 1}
            </span>
            <div>
              <p className="text-xs font-semibold text-gray-700">{step.label}</p>
              {step.description && (
                <p className="text-xs text-gray-500 mt-0.5">{step.description}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
