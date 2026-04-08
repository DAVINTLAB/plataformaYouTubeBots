import { useCallback, useState } from "react";
import type { UserCommentsResponse } from "../../api/annotate";

interface Props {
  data: UserCommentsResponse;
  onAnnotate: (
    entryId: string,
    label: "bot" | "humano",
    justificativa?: string | null
  ) => Promise<void>;
  onBack: () => void;
  readOnly?: boolean;
}

export function UserCommentsList({ data, onAnnotate, onBack, readOnly = false }: Props) {
  const [justificativa, setJustificativa] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const currentLabel = data.my_annotation?.label ?? null;

  const handleClassify = useCallback(
    async (label: "bot" | "humano") => {
      if (submitting) return;
      const just = label === "bot" ? justificativa : undefined;
      if (label === "bot" && !just?.trim()) return;
      setSubmitting(true);
      await onAnnotate(data.entry_id, label, just);
      setSubmitting(false);
    },
    [onAnnotate, data.entry_id, justificativa, submitting]
  );

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <button
            className="text-xs font-medium text-davint-400 hover:underline mb-2"
            onClick={onBack}
          >
            &larr; Voltar para lista de usuários
          </button>
          <h2 className="text-lg font-bold text-gray-800">{data.author_display_name}</h2>
          <p className="text-xs text-gray-500">
            {data.author_channel_id} &middot; {data.comments.length} comentários
          </p>
        </div>
        {currentLabel && (
          <span
            className={[
              "text-sm font-semibold px-3 py-1 rounded-full",
              currentLabel === "bot" ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600",
            ].join(" ")}
          >
            {currentLabel === "bot" ? "Bot" : "Humano"}
          </span>
        )}
      </div>

      {/* Anotação de todos os anotadores (admin) */}
      {data.all_annotations && data.all_annotations.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
            Anotações dos pesquisadores
          </h3>
          <div className="flex flex-col gap-2">
            {data.all_annotations.map((a, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span className="font-medium text-gray-700">{a.annotator_name}</span>
                <span
                  className={[
                    "text-[11px] font-semibold px-2 py-0.5 rounded-full",
                    a.label === "bot" ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600",
                  ].join(" ")}
                >
                  {a.label}
                </span>
                {a.justificativa && (
                  <span className="text-xs text-gray-500 italic">{a.justificativa}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Classificação do usuário (pesquisador) */}
      {!readOnly && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Classificar este usuário</h3>
          <p className="text-xs text-gray-500 mb-3">
            Analise todos os comentários abaixo e classifique o autor como bot ou humano.
          </p>

          {/* Justificativa (obrigatória para bot) */}
          <div className="mb-3">
            <label className="text-xs text-gray-600 block mb-1">
              Justificativa (obrigatória para Bot)
            </label>
            <textarea
              className="form-input text-sm"
              rows={2}
              placeholder="Ex: padrão de spam, texto repetitivo..."
              value={justificativa}
              onChange={(e) => setJustificativa(e.target.value)}
            />
            {!justificativa.trim() && (
              <p className="text-[11px] text-yellow-600 mt-1">
                Preencha a justificativa acima para habilitar a classificação como Bot.
              </p>
            )}
          </div>

          <div className="flex gap-4">
            <button
              className={[
                "flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold transition-colors",
                currentLabel === "humano"
                  ? "bg-green-500 text-white shadow-sm"
                  : "bg-green-50 text-green-700 border border-green-200 hover:bg-green-100",
              ].join(" ")}
              onClick={() => handleClassify("humano")}
              disabled={submitting}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-5 h-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"
                />
              </svg>
              Humano
            </button>
            <button
              className={[
                "flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold transition-colors",
                currentLabel === "bot"
                  ? "bg-red-500 text-white shadow-sm"
                  : "bg-red-50 text-red-700 border border-red-200 hover:bg-red-100",
                !justificativa.trim() || submitting ? "opacity-50 cursor-not-allowed" : "",
              ].join(" ")}
              onClick={() => handleClassify("bot")}
              disabled={submitting || !justificativa.trim()}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-5 h-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 0 0 2.25-2.25V6.75a2.25 2.25 0 0 0-2.25-2.25H6.75A2.25 2.25 0 0 0 4.5 6.75v10.5a2.25 2.25 0 0 0 2.25 2.25Zm.75-12h9v9h-9v-9Z"
                />
              </svg>
              Bot
            </button>
          </div>

          {data.my_annotation && (
            <p className="text-[11px] text-gray-400 mt-2">
              Anotado como <strong>{data.my_annotation.label}</strong>
              {data.my_annotation.justificativa && <> &mdash; {data.my_annotation.justificativa}</>}
            </p>
          )}
        </div>
      )}

      {/* Dica */}
      {!readOnly && (
        <div className="flex items-start gap-2 p-3 bg-davint-50 rounded-lg mb-4">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-4 h-4 text-davint-500 flex-shrink-0 mt-0.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
            />
          </svg>
          <p className="text-xs text-davint-700">
            Os comentários abaixo são <strong>evidências</strong> para fundamentar sua decisão sobre
            o autor. A classificação é única para o usuário, não por comentário.
          </p>
        </div>
      )}

      {/* Comentários (apenas como evidências — sem botões de anotação por comment) */}
      <div className="flex flex-col gap-3">
        {data.comments.map((comment) => (
          <div
            key={comment.comment_db_id}
            className="bg-white rounded-xl border border-gray-200 p-4"
          >
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{comment.text_original}</p>
            <div className="flex gap-4 mt-2 text-[11px] text-gray-400">
              <span>{new Date(comment.published_at).toLocaleDateString("pt-BR")}</span>
              <span>{comment.like_count} likes</span>
              <span>{comment.reply_count} respostas</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
