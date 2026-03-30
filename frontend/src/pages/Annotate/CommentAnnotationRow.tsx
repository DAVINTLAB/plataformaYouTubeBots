import { useCallback, useEffect, useRef, useState } from "react";
import type { CommentWithAnnotation } from "../../api/annotate";

interface Props {
  comment: CommentWithAnnotation;
  focused: boolean;
  onAnnotate: (
    commentDbId: string,
    label: "bot" | "humano",
    justificativa?: string | null
  ) => Promise<void>;
  onFocus: () => void;
  readOnly?: boolean;
}

export function CommentAnnotationRow({
  comment,
  focused,
  onAnnotate,
  onFocus,
  readOnly = false,
}: Props) {
  const [showJustificativa, setShowJustificativa] = useState(false);
  const [justificativa, setJustificativa] = useState(comment.my_annotation?.justificativa ?? "");
  const [saving, setSaving] = useState(false);
  const rowRef = useRef<HTMLDivElement>(null);

  const currentLabel = comment.my_annotation?.label ?? null;

  useEffect(() => {
    if (focused && rowRef.current) {
      rowRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [focused]);

  const handleHumano = useCallback(async () => {
    setSaving(true);
    setShowJustificativa(false);
    await onAnnotate(comment.comment_db_id, "humano", null);
    setSaving(false);
  }, [comment.comment_db_id, onAnnotate]);

  const handleBotClick = useCallback(() => {
    setShowJustificativa(true);
    onFocus();
  }, [onFocus]);

  const handleBotConfirm = useCallback(async () => {
    if (!justificativa.trim()) return;
    setSaving(true);
    await onAnnotate(comment.comment_db_id, "bot", justificativa.trim());
    setShowJustificativa(false);
    setSaving(false);
  }, [comment.comment_db_id, justificativa, onAnnotate]);

  // Atalhos de teclado
  useEffect(() => {
    if (!focused) return;
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return;
      if (e.key === "h" || e.key === "H") {
        e.preventDefault();
        void handleHumano();
      } else if (e.key === "b" || e.key === "B") {
        e.preventDefault();
        handleBotClick();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [focused, handleHumano, handleBotClick]);

  const date = new Date(comment.published_at).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      ref={rowRef}
      onClick={onFocus}
      className={[
        "p-4 rounded-lg border transition-all",
        focused
          ? "border-davint-400 bg-davint-50/30 ring-1 ring-davint-400/20"
          : "border-gray-200 bg-white",
      ].join(" ")}
    >
      {/* Texto do comentário */}
      <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed mb-2">
        {comment.text_original}
      </p>

      {/* Metadados */}
      <div className="flex items-center gap-3 text-[11px] text-gray-400 mb-3">
        <span>{date}</span>
        <span>{comment.like_count} curtidas</span>
        <span>{comment.reply_count} respostas</span>
      </div>

      {/* Badge atual + botões */}
      <div className="flex items-center gap-2 flex-wrap">
        {currentLabel && (
          <span
            className={[
              "text-[11px] font-semibold px-2.5 py-0.5 rounded-full",
              currentLabel === "bot" ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600",
            ].join(" ")}
          >
            {currentLabel === "bot" ? "Bot" : "Humano"}
          </span>
        )}

        {!readOnly && (
          <div className="flex gap-1.5 ml-auto">
            <button
              className={[
                "px-3 py-1 text-xs font-medium rounded-md border transition-colors inline-flex items-center gap-1",
                currentLabel === "humano"
                  ? "bg-green-50 border-green-300 text-green-700"
                  : "bg-white border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600",
              ].join(" ")}
              disabled={saving}
              onClick={handleHumano}
              title="Atalho: H"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-3.5 h-3.5"
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
                "px-3 py-1 text-xs font-medium rounded-md border transition-colors inline-flex items-center gap-1",
                currentLabel === "bot"
                  ? "bg-red-50 border-red-300 text-red-700"
                  : "bg-white border-gray-200 text-gray-600 hover:border-red-300 hover:text-red-600",
              ].join(" ")}
              disabled={saving}
              onClick={handleBotClick}
              title="Atalho: B"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-3.5 h-3.5"
              >
                <rect
                  x="4"
                  y="8"
                  width="16"
                  height="12"
                  rx="3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                />
                <circle cx="9" cy="14" r="1.5" />
                <circle cx="15" cy="14" r="1.5" />
                <line
                  x1="12"
                  y1="4"
                  x2="12"
                  y2="8"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
                <circle
                  cx="12"
                  cy="3"
                  r="1.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                />
                <line
                  x1="1"
                  y1="13"
                  x2="4"
                  y2="13"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
                <line
                  x1="20"
                  y1="13"
                  x2="23"
                  y2="13"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
              Bot
            </button>
          </div>
        )}
      </div>

      {/* Campo justificativa (inline) */}
      {showJustificativa && (
        <div className="mt-3 flex flex-col gap-2">
          <textarea
            className="form-input text-sm"
            placeholder="Justifique a classificação como bot..."
            value={justificativa}
            onChange={(e) => setJustificativa(e.target.value)}
            rows={2}
            autoFocus
          />
          <div className="flex gap-2">
            <button
              className="btn btn-primary btn-sm"
              disabled={!justificativa.trim() || saving}
              onClick={handleBotConfirm}
            >
              {saving ? "Salvando..." : "Confirmar Bot"}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowJustificativa(false)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Justificativa existente (readonly — pesquisador) */}
      {!readOnly &&
        currentLabel === "bot" &&
        comment.my_annotation?.justificativa &&
        !showJustificativa && (
          <p className="mt-2 text-xs text-gray-500 italic">
            Justificativa: {comment.my_annotation.justificativa}
          </p>
        )}

      {/* Admin: anotações de todos os pesquisadores */}
      {readOnly && comment.all_annotations && comment.all_annotations.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-2 flex flex-col gap-1.5">
          {comment.all_annotations.map((ann, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className="font-medium text-gray-700">{ann.annotator_name}:</span>
              <span
                className={[
                  "font-semibold px-2 py-0.5 rounded-full",
                  ann.label === "bot" ? "bg-red-50 text-red-600" : "bg-green-50 text-green-600",
                ].join(" ")}
              >
                {ann.label === "bot" ? "Bot" : "Humano"}
              </span>
              {ann.justificativa && (
                <span className="text-gray-400 italic truncate max-w-xs">{ann.justificativa}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Sem anotação (admin) */}
      {readOnly && (!comment.all_annotations || comment.all_annotations.length === 0) && (
        <p className="mt-2 text-[11px] text-gray-400 italic">Nenhuma anotação ainda.</p>
      )}
    </div>
  );
}
