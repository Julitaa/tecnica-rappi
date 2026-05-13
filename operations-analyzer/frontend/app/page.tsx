"use client";
import { useState } from "react";
import { ChatWindow } from "@/components/chat-window";
import { ReportPanel } from "@/components/report-panel";
import { Button } from "@/components/ui/button";

export default function Home() {
  const [showReport, setShowReport] = useState(false);
  return (
    <main className="h-screen flex flex-col">
      <header className="bg-rappi text-white px-6 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">Operations Analyzer</h1>
        <Button
          variant="outline"
          className="bg-white text-rappi border-white hover:bg-gray-100"
          onClick={() => setShowReport((v) => !v)}
        >
          {showReport ? "Ocultar reporte" : "Generar reporte ejecutivo"}
        </Button>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <section className={`${showReport ? "w-1/2" : "w-full"} border-r border-gray-200 transition-all`}>
          <ChatWindow />
        </section>
        {showReport && (
          <section className="w-1/2 overflow-y-auto">
            <ReportPanel />
          </section>
        )}
      </div>
    </main>
  );
}
