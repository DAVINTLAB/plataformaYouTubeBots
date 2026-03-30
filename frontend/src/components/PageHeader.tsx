import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { reviewApi } from "../api/review";
import { useAuthContext } from "../contexts/AuthContext";
import { useAuth } from "../pages/Auth/useAuth";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  user: "Anotador",
};

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  breadcrumbs?: BreadcrumbItem[];
  onChangePassword?: () => void;
}

export function PageHeader({ breadcrumbs, onChangePassword }: PageHeaderProps) {
  const { user, isAdmin, token } = useAuthContext();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [pendingConflicts, setPendingConflicts] = useState(0);

  useEffect(() => {
    if (!isAdmin || !token) return;
    reviewApi
      .stats(token)
      .then((s) => setPendingConflicts(s.pending_conflicts))
      .catch(() => {});
  }, [isAdmin, token]);

  return (
    <header className="flex items-center justify-between px-8 h-[60px] bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="bg-transparent border-0 p-0 cursor-pointer flex-shrink-0"
          aria-label="Voltar ao início"
        >
          <img src="/davint-logo.png" alt="DaVint Lab" className="h-7 w-auto" />
        </button>
        <span className="inline-block w-px h-5 bg-gray-200" aria-hidden="true" />
        {breadcrumbs && breadcrumbs.length > 0 ? (
          <nav className="flex items-center gap-1.5 text-sm" aria-label="Breadcrumb">
            {breadcrumbs.map((crumb, i) => (
              <Fragment key={crumb.label}>
                {i > 0 && (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={2.5}
                    stroke="currentColor"
                    className="w-3 h-3 text-gray-300 flex-shrink-0"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M8.25 4.5l7.5 7.5-7.5 7.5"
                    />
                  </svg>
                )}
                {crumb.to ? (
                  <button
                    onClick={() => navigate(crumb.to!)}
                    className="font-semibold text-gray-500 hover:text-davint-400 transition-colors bg-transparent border-0 cursor-pointer p-0"
                  >
                    {crumb.label}
                  </button>
                ) : (
                  <span className="font-semibold text-gray-800">{crumb.label}</span>
                )}
              </Fragment>
            ))}
          </nav>
        ) : (
          <span className="text-sm font-semibold text-gray-500">Plataforma YouTube Bots</span>
        )}
      </div>

      <div className="flex items-center gap-4">
        {isAdmin && pendingConflicts > 0 && (
          <button
            onClick={() => navigate("/review")}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-yellow-50 border border-yellow-200 text-yellow-700 text-xs font-semibold hover:bg-yellow-100 transition-colors"
            title="Há conflitos pendentes de revisão"
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
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
            Conflitos pendentes
          </button>
        )}
        <span className="flex items-center gap-2 text-sm text-gray-500">
          <span className={`badge ${isAdmin ? "badge-admin" : "badge-user"}`}>
            {user ? (ROLE_LABEL[user.role] ?? user.role) : ""}
          </span>
          <span className="flex flex-col items-end leading-tight">
            <span className="text-gray-800 font-medium text-sm">{user?.name}</span>
            <span className="text-gray-400 text-xs">{user?.username}</span>
          </span>
        </span>
        {onChangePassword && (
          <button className="btn btn-ghost" onClick={onChangePassword}>
            Alterar senha
          </button>
        )}
        <button className="btn btn-ghost" onClick={() => void logout()}>
          Sair
        </button>
      </div>
    </header>
  );
}
