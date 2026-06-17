import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <section className="max-w-md rounded-lg border border-slate-200 bg-white p-6 text-center shadow-panel">
        <h1 className="text-xl font-bold text-slate-950">Vista no encontrada</h1>
        <p className="mt-2 text-sm text-slate-500">La ruta solicitada no existe en AgroEscudo.</p>
        <Link
          href="/"
          className="mt-4 inline-flex rounded-md bg-emeraldTech px-4 py-2 text-sm font-semibold text-white hover:bg-emeraldDeep"
        >
          Volver al dashboard
        </Link>
      </section>
    </main>
  );
}
