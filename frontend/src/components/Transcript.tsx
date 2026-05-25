"use client";

import {
  useChat,
  useLocalParticipant,
  useParticipantTracks,
  useTrackTranscription,
  useTranscriptions,
  useVoiceAssistant,
  type ReceivedChatMessage,
  type TextStreamData,
} from "@livekit/components-react";
import type { ReceivedTranscriptionSegment } from "@livekit/components-core";
import clsx from "clsx";
import { Track } from "livekit-client";
import { useMemo, useEffect, useRef } from "react";

type TranscriptRow = {
  key: string;
  sortMs: number;
  text: string;
  role: "user" | "agent";
};

/** Latest segment per id (streamed STT/TTS captions update in place). */
function latestSegmentsById(segments: ReceivedTranscriptionSegment[]): ReceivedTranscriptionSegment[] {
  const map = new Map<string, ReceivedTranscriptionSegment>();
  for (const s of segments) {
    map.set(s.id, s);
  }
  return [...map.values()];
}

function normalizeText(t: string): string {
  return t.replace(/\s+/g, " ").trim().toLowerCase();
}

/** Drop duplicate role+text (same line often appears on both text stream + track transcription). */
function dedupeRows(rows: TranscriptRow[]): TranscriptRow[] {
  const seen = new Set<string>();
  const out: TranscriptRow[] = [];
  for (const r of rows) {
    const key = `${r.role}:${normalizeText(r.text)}`;
    if (!r.text.trim() || seen.has(key)) continue;
    seen.add(key);
    out.push(r);
  }
  return out;
}

function sortTranscriptionStreams(streams: TextStreamData[]): TextStreamData[] {
  return [...streams].sort((a, b) => {
    const ta = a.streamInfo.timestamp ?? 0;
    const tb = b.streamInfo.timestamp ?? 0;
    if (ta !== tb) return ta - tb;
    return String(a.streamInfo.id).localeCompare(String(b.streamInfo.id));
  });
}

function chatMessageRole(msg: ReceivedChatMessage, localId: string | undefined): "user" | "agent" {
  const ident = msg.from?.identity ?? "";
  if (localId && ident === localId) return "user";
  if (ident.startsWith("agent") || msg.from?.name === "Viona AI") return "agent";
  return "agent";
}

/**
 * Voice agents may send captions via:
 * - `lk.transcription` text streams → `useTranscriptions()`
 * - track-linked `TranscriptionSegment`s → `useTrackTranscription` on agent / user mic
 * - optional `lk.chat` → `useChat()`
 * We merge so at least one path populates the UI even on older servers / mixed modes.
 */
export default function Transcript() {
  const transcriptionStreams = useTranscriptions();
  const { chatMessages } = useChat();
  const { localParticipant } = useLocalParticipant();
  const { agentTranscriptions } = useVoiceAssistant();
  const micRefs = useParticipantTracks(
    [Track.Source.Microphone],
    localParticipant?.identity,
  );
  const { segments: userMicSegments } = useTrackTranscription(micRefs[0]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const localId = localParticipant?.identity;

  const rows = useMemo(() => {
    const acc: TranscriptRow[] = [];

    for (const stream of sortTranscriptionStreams(transcriptionStreams)) {
      const text = stream.text?.trim() ?? "";
      if (!text) continue;
      const isUser = localId !== undefined && stream.participantInfo.identity === localId;
      acc.push({
        key: `ts-${stream.streamInfo.id}`,
        sortMs: stream.streamInfo.timestamp ?? 0,
        text,
        role: isUser ? "user" : "agent",
      });
    }

    for (const seg of latestSegmentsById(agentTranscriptions)) {
      const text = seg.text?.trim() ?? "";
      if (!text) continue;
      acc.push({
        key: `ag-${seg.id}`,
        sortMs: seg.firstReceivedTime,
        text,
        role: "agent",
      });
    }

    for (const seg of latestSegmentsById(userMicSegments)) {
      const text = seg.text?.trim() ?? "";
      if (!text) continue;
      acc.push({
        key: `me-${seg.id}`,
        sortMs: seg.firstReceivedTime,
        text,
        role: "user",
      });
    }

    for (const msg of chatMessages) {
      const text = (msg.message ?? "").trim();
      if (!text) continue;
      acc.push({
        key: `chat-${msg.id}`,
        sortMs: msg.timestamp,
        text,
        role: chatMessageRole(msg, localId),
      });
    }

    acc.sort((a, b) => {
      if (a.sortMs !== b.sortMs) return a.sortMs - b.sortMs;
      return a.key.localeCompare(b.key);
    });

    return dedupeRows(acc);
  }, [
    transcriptionStreams,
    agentTranscriptions,
    userMicSegments,
    chatMessages,
    localId,
  ]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [rows]);

  if (!rows.length) {
    return (
      <div className="h-full bg-slate-800/40 rounded-2xl border border-slate-700 flex flex-col items-center justify-center px-6 py-8 gap-2">
        <p className="text-slate-400 text-sm text-center">Transkrip percakapan akan muncul di sini...</p>
        <p className="text-slate-600 text-xs text-center max-w-xs">
          Pastikan mikrofon menyala (tidak bisu). Teks diambil dari transkrip suara LiveKit dan chat ruangan.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full bg-slate-800/40 rounded-2xl border border-slate-700 flex flex-col">
      <div className="px-4 py-3 border-b border-slate-700">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Transkrip</p>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {rows.map((row) => (
          <div
            key={row.key}
            className={clsx(
              "flex gap-3 animate-fade-in",
              row.role === "agent" ? "flex-row" : "flex-row-reverse",
            )}
          >
            <div
              className={clsx(
                "w-7 h-7 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5",
                row.role === "agent" ? "bg-blue-600" : "bg-slate-600",
              )}
            >
              {row.role === "agent" ? "🤖" : "👤"}
            </div>
            <div
              className={clsx(
                "max-w-[80%] px-4 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words",
                row.role === "agent"
                  ? "bg-slate-700 text-slate-100 rounded-tl-sm"
                  : "bg-blue-600 text-white rounded-tr-sm",
              )}
            >
              {row.text}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
