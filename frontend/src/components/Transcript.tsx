"use client";

import { useChat } from "@livekit/components-react";
import { useEffect, useRef } from "react";
import clsx from "clsx";

export default function Transcript() {
  const { chatMessages } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  if (!chatMessages.length) {
    return (
      <div className="h-full bg-slate-800/40 rounded-2xl border border-slate-700 flex items-center justify-center">
        <p className="text-slate-500 text-sm">Transkrip percakapan akan muncul di sini...</p>
      </div>
    );
  }

  return (
    <div className="h-full bg-slate-800/40 rounded-2xl border border-slate-700 flex flex-col">
      <div className="px-4 py-3 border-b border-slate-700">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Transkrip</p>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {chatMessages.map((msg) => {
          const isAgent = msg.from?.identity?.startsWith("agent") || msg.from?.name === "Viona AI";
          return (
            <div
              key={msg.id}
              className={clsx(
                "flex gap-3 animate-fade-in",
                isAgent ? "flex-row" : "flex-row-reverse",
              )}
            >
              <div className={clsx(
                "w-7 h-7 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5",
                isAgent ? "bg-blue-600" : "bg-slate-600",
              )}>
                {isAgent ? "🤖" : "👤"}
              </div>
              <div className={clsx(
                "max-w-[80%] px-4 py-2 rounded-2xl text-sm leading-relaxed",
                isAgent
                  ? "bg-slate-700 text-slate-100 rounded-tl-sm"
                  : "bg-blue-600 text-white rounded-tr-sm",
              )}>
                {msg.message}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
