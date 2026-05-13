"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/lib/types";

export function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[80%] rounded-lg px-4 py-2 ${
        isUser
          ? "bg-rappi text-white"
          : "bg-gray-100 text-gray-900 border border-gray-200"
      }`}>
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>
        {msg.toolsUsed && msg.toolsUsed.length > 0 && (
          <div className="text-xs text-gray-500 mt-2">
            Tools: {msg.toolsUsed.join(", ")}
          </div>
        )}
      </div>
    </div>
  );
}
