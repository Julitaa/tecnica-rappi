"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { reportPdfUrl } from "@/lib/api-client";

interface ReportPanelProps {
  markdown: string;
  onRegenerate: () => void;
  isRegenerating: boolean;
}

export function ReportPanel({ markdown, onRegenerate, isRegenerating }: ReportPanelProps) {
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
    <div className="h-full">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-rappi">Reporte Ejecutivo</h2>
        <Button onClick={downloadPdf} className="bg-rappi hover:bg-rappi/90 text-white" disabled={isRegenerating}>
          Descargar PDF
        </Button>
      </div>
      <article className="prose prose-sm max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </article>
    </div>
  );
}
