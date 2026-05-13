export type ChatEvent =
  | { type: "token"; content: string }
  | { type: "tool"; name: string; args: Record<string, unknown> }
  | { type: "done"; sources: string[]; suggestions: string[] };

export type Message = {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  suggestions?: string[];
};
