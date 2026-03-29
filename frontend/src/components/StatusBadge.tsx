const LABEL: Record<string, string> = {
  pending: "Aguardando",
  running: "Coletando comentários",
  completed: "Concluída",
  failed: "Falhou",
  enriching_video: "Obtendo dados do vídeo",
  enriching_replies: "Coletando respostas",
  enriching_channels: "Coletando dados dos autores",
  enriching: "Enriquecendo dados",
};

const COLOR: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700",
  running: "bg-blue-50 text-blue-700",
  completed: "bg-green-50 text-green-600",
  failed: "bg-red-50 text-red-600",
  enriching_video: "bg-purple-50 text-purple-700",
  enriching_replies: "bg-purple-50 text-purple-700",
  enriching_channels: "bg-purple-50 text-purple-700",
  enriching: "bg-purple-50 text-purple-700",
};

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const padding = size === "sm" ? "px-2 py-0.5" : "px-2.5 py-0.5";
  return (
    <span
      className={`text-[11px] font-semibold rounded-full ${padding} ${COLOR[status] ?? "bg-gray-100 text-gray-400"}`}
    >
      {LABEL[status] ?? status}
    </span>
  );
}
