"use client";
import { useEffect, useRef, useState } from "react";
import { v4 as uuid } from "uuid";
import { MessageBubble } from "./message-bubble";
import { MessageInput } from "./message-input";
import { streamChat } from "@/lib/api-client";
import type { Message } from "@/lib/types";

export function ChatWindow() {
  const [sessionId] = useState(() => {
    if (typeof window === "undefined") return uuid();
    const stored = localStorage.getItem("session_id");
    if (stored) return stored;
    const fresh = uuid();
    localStorage.setItem("session_id", fresh);
    return fresh;
  });
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    setSuggestions([]);
    setMessages((m) => [...m, { role: "user", content: text }]);
    setMessages((m) => [...m, { role: "assistant", content: "" }]);
    setStreaming(true);
    const toolsUsed: string[] = [];
    try {
      for await (const ev of streamChat(sessionId, text)) {
        if (ev.type === "token") {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              content: copy[copy.length - 1].content + ev.content,
            };
            return copy;
          });
        } else if (ev.type === "tool") {
          toolsUsed.push(ev.name);
        } else if (ev.type === "done") {
          setMessages((m) => {
            const copy = [...m];
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              toolsUsed: ev.sources,
              suggestions: ev.suggestions,
            };
            return copy;
          });
          setSuggestions(ev.suggestions);
        }
      }
    } catch (e) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          role: "assistant",
          content: `Error: ${e instanceof Error ? e.message : String(e)}`,
        };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-12">
            <p className="text-lg">Preguntame sobre las métricas operacionales.</p>
            <p className="text-sm mt-2">Ej: "¿Cuáles son las 5 zonas con mayor Lead Penetration esta semana?"</p>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} msg={m} />
        ))}
        <div ref={endRef} />
      </div>
      <MessageInput
        onSend={send}
        disabled={streaming}
        suggestions={suggestions}
        onSuggest={(s) => send(s)}
      />
    </div>
  );
}
