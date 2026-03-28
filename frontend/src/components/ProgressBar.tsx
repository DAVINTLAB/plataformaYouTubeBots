interface ProgressBarProps {
  /** Percentual 0-100. Ignorado quando `indeterminate` é true. */
  percent?: number;
  /** Quando true exibe animação de pulso sem percentual fixo. */
  indeterminate?: boolean;
  label?: string;
  size?: "sm" | "md";
}

export function ProgressBar({
  percent = 0,
  indeterminate = false,
  label,
  size = "md",
}: ProgressBarProps) {
  const height = size === "sm" ? "h-1" : "h-1.5";
  return (
    <div className="flex flex-col gap-1">
      <div className={`${height} w-full bg-gray-100 rounded-full overflow-hidden`}>
        {indeterminate ? (
          <div className={`${height} bg-davint-400 animate-pulse rounded-full w-3/4`} />
        ) : (
          <div
            className={`${height} bg-davint-400 rounded-full transition-all duration-150`}
            style={{ width: `${percent}%` }}
          />
        )}
      </div>
      {label && <p className="text-sm text-gray-500">{label}</p>}
    </div>
  );
}
