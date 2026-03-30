import { useCallback, useState } from "react";
import type { UserCommentsResponse } from "../../api/annotate";
import { ProgressBar } from "../../components/ProgressBar";
import { CommentAnnotationRow } from "./CommentAnnotationRow";

interface Props {
  data: UserCommentsResponse;
  onAnnotate: (
    commentDbId: string,
    label: "bot" | "humano",
    justificativa?: string | null
  ) => Promise<void>;
  onBack: () => void;
  readOnly?: boolean;
}

export function UserCommentsList({ data, onAnnotate, onBack, readOnly = false }: Props) {
  const [focusedIndex, setFocusedIndex] = useState(0);

  const annotated = data.comments.filter((c) => c.my_annotation !== null).length;
  const total = data.comments.length;
  const percent = total > 0 ? Math.round((annotated / total) * 100) : 0;

  const handleAnnotate = useCallback(
    async (commentDbId: string, label: "bot" | "humano", justificativa?: string | null) => {
      await onAnnotate(commentDbId, label, justificativa);
    },
    [onAnnotate]
  );

  // Tab navega entre comentários
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Tab") {
        e.preventDefault();
        setFocusedIndex((prev) =>
          e.shiftKey ? Math.max(0, prev - 1) : Math.min(data.comments.length - 1, prev + 1)
        );
      }
    },
    [data.comments.length]
  );

  return (
    <div onKeyDown={handleKeyDown}>
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
            {data.author_channel_id} &middot; {total} comentários
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-gray-700">
            {annotated}/{total} anotados
          </p>
          <ProgressBar percent={percent} size="sm" />
        </div>
      </div>

      {/* Dica atalhos */}
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
            Atalhos:{" "}
            <kbd className="px-1 py-0.5 bg-white border border-gray-200 rounded text-[10px] font-mono">
              H
            </kbd>{" "}
            = Humano,{" "}
            <kbd className="px-1 py-0.5 bg-white border border-gray-200 rounded text-[10px] font-mono">
              B
            </kbd>{" "}
            = Bot,{" "}
            <kbd className="px-1 py-0.5 bg-white border border-gray-200 rounded text-[10px] font-mono">
              Tab
            </kbd>{" "}
            = próximo comentário
          </p>
        </div>
      )}

      {/* Comentários */}
      <div className="flex flex-col gap-3">
        {data.comments.map((comment, i) => (
          <CommentAnnotationRow
            key={comment.comment_db_id}
            comment={comment}
            focused={!readOnly && i === focusedIndex}
            onAnnotate={handleAnnotate}
            onFocus={() => setFocusedIndex(i)}
            readOnly={readOnly}
          />
        ))}
      </div>
    </div>
  );
}
