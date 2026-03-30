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

export function CommentAnnotationRow({ comment, focused, onAnnotate, onFocus, readOnly = false }: Props) {
  const [showJustificativa, setShowJustificativa] = useState(false);
  const [justificativa, setJustificativa] = useState(
    comment.my_annotation?.justificativa ?? ""
  );
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
        focused ? "border-davint-400 bg-davint-50/30 ring-1 ring-davint-400/20" : "border-gray-200 bg-white",
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
              currentLabel === "bot"
                ? "bg-red-50 text-red-600"
                : "bg-green-50 text-green-600",
            ].join(" ")}
          >
            {currentLabel === "bot" ? "Bot" : "Humano"}
          </span>
        )}

        {!readOnly && (
          <div className="flex gap-1.5 ml-auto">
            <button
              className={[
                "px-3 py-1 text-xs font-medium rounded-md border transition-colors",
                currentLabel === "humano"
                  ? "bg-green-50 border-green-300 text-green-700"
                  : "bg-white border-gray-200 text-gray-600 hover:border-green-300 hover:text-green-600",
              ].join(" ")}
              disabled={saving}
              onClick={handleHumano}
              title="Atalho: H"
            >
              Humano
            </button>
            <button
              className={[
                "px-3 py-1 text-xs font-medium rounded-md border transition-colors",
                currentLabel === "bot"
                  ? "bg-red-50 border-red-300 text-red-700"
                  : "bg-white border-gray-200 text-gray-600 hover:border-red-300 hover:text-red-600",
              ].join(" ")}
              disabled={saving}
              onClick={handleBotClick}
              title="Atalho: B"
            >
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
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setShowJustificativa(false)}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Justificativa existente (readonly — pesquisador) */}
      {!readOnly && currentLabel === "bot" && comment.my_annotation?.justificativa && !showJustificativa && (
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
                  ann.label === "bot"
                    ? "bg-red-50 text-red-600"
                    : "bg-green-50 text-green-600",
                ].join(" ")}
              >
                {ann.label === "bot" ? "Bot" : "Humano"}
              </span>
              {ann.justificativa && (
                <span className="text-gray-400 italic truncate max-w-xs">
                  {ann.justificativa}
                </span>
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
