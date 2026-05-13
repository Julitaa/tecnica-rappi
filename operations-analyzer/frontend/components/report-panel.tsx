"use client";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { fetchReportMarkdown, reportPdfUrl } from "@/lib/api-client";

export function ReportPanel() {
  const [md, setMd] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchReportMarkdown()
      .then((text) => { if (!cancelled) setMd(text); })
      .catch((e) => { if (!cancelled) setError(String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const downloadPdf = async () => {
    const res = await fetch(reportPdfUrl(), { method: "POST" });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rappi-insights.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-rappi">Reporte Ejecutivo</h2>
        <Button onClick={downloadPdf} className="bg-rappi hover:bg-rappi/90" disabled={loading || !!error}>
          Descargar PDF
        </Button>
      </div>
      {loading && <p className="text-gray-500">Generando reporte... (esto puede tardar 20-40 segundos)</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      {!loading && !error && (
        <article className="prose prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
        </article>
      )}
    </div>
  );
}
