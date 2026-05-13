"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function MessageInput({ onSend, disabled, suggestions, onSuggest }: {
  onSend: (msg: string) => void;
  disabled: boolean;
  suggestions: string[];
  onSuggest: (s: string) => void;
}) {
  const [value, setValue] = useState("");
  const send = () => {
    const v = value.trim();
    if (!v) return;
    onSend(v);
    setValue("");
  };
  return (
    <div className="border-t border-gray-200 p-4 bg-[#FFF8F5]">
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggest(s)}
              className="text-xs px-3 py-1 rounded-full border border-rappi text-rappi hover:bg-rappi hover:text-white transition"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Hacé una pregunta sobre las métricas..."
          className="text-gray-900 placeholder:text-gray-400 bg-white"
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
          disabled={disabled}
        />
        <Button onClick={send} disabled={disabled} className="bg-rappi hover:bg-rappi/90 text-white">
          Enviar
        </Button>
      </div>
    </div>
  );
}
