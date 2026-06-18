import { AlertTriangle } from "lucide-react";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-panel border border-red-200 bg-red-50 p-5 text-red-900 shadow-soft">
      <div className="flex items-start gap-3">
        <AlertTriangle size={20} aria-hidden="true" />
        <div>
          <p className="font-semibold">Error de conexion</p>
          <p className="mt-1 whitespace-pre-line text-sm">{message}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 rounded-lg bg-red-700 px-3 py-2 text-sm font-bold text-white hover:bg-red-800"
            >
              Reintentar conexión
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
