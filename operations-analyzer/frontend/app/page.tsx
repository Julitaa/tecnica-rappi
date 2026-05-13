"use client";
import { useState } from "react";
import { ChatWindow } from "@/components/chat-window";
import { ReportPanel } from "@/components/report-panel";
import { Button } from "@/components/ui/button";
import { fetchReportMarkdown } from "@/lib/api-client";

export default function Home() {
  const [showReport, setShowReport] = useState(false);
  const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  const generateReport = async () => {
    setLoadingReport(true);
    try {
      const markdown = await fetchReportMarkdown();
      setReportMarkdown(markdown);
      setShowReport(true);
    } catch (error) {
      console.error("Error generating report:", error);
    } finally {
      setLoadingReport(false);
    }
  };

  const regenerateReport = async () => {
    await generateReport();
  };

  return (
    <main className="h-screen flex flex-col">
      <header className="bg-rappi text-white px-6 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">Operations Analyzer</h1>
        <div className="flex gap-2">
          {reportMarkdown && (
            <Button
              variant="outline"
              className="bg-white text-rappi border-white hover:bg-gray-100"
              onClick={regenerateReport}
              disabled={loadingReport}
            >
              {loadingReport ? "Regenerando..." : "Regenerar reporte"}
            </Button>
          )}
          {reportMarkdown ? (
            <Button
              variant="outline"
              className="bg-white text-rappi border-white hover:bg-gray-100"
              onClick={() => setShowReport((v) => !v)}
            >
              {showReport ? "Ocultar reporte" : "Ver reporte"}
            </Button>
          ) : (
            <Button
              variant="outline"
              className="bg-white text-rappi border-white hover:bg-gray-100"
              onClick={generateReport}
              disabled={loadingReport}
            >
              {loadingReport ? "Generando..." : "Generar reporte ejecutivo"}
            </Button>
          )}
        </div>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <section className={`${showReport ? "w-1/2" : "w-full"} border-r-4 border-rappi transition-all px-6 py-4`}>
          <ChatWindow />
        </section>
        {showReport && reportMarkdown && (
          <section className="w-1/2 overflow-y-auto px-6 py-4">
            <ReportPanel markdown={reportMarkdown} onRegenerate={regenerateReport} isRegenerating={loadingReport} />
          </section>
        )}
      </div>
    </main>
  );
}
