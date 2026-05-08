"use client";

import { useCallback, useState } from "react";
import { ingestPDF, ingestText } from "@/lib/api";
import { Upload, FileText, CheckCircle, AlertCircle } from "lucide-react";
import clsx from "clsx";

type Status = "idle" | "uploading" | "success" | "error";

export default function FAQUpload() {
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [category, setCategory] = useState("faq");
  const [textMode, setTextMode] = useState(false);
  const [textContent, setTextContent] = useState("");
  const [textSource, setTextSource] = useState("manual");

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.endsWith(".pdf")) {
      setStatus("error");
      setMessage("Hanya file PDF yang didukung.");
      return;
    }
    setStatus("uploading");
    setMessage("");
    try {
      const result = await ingestPDF(file, category);
      setStatus("success");
      setMessage(`✓ ${file.name}: ${result.chunks} chunk berhasil diingest.`);
    } catch (e) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Upload gagal.");
    }
  }, [category]);

  const handleTextSubmit = useCallback(async () => {
    if (!textContent.trim()) return;
    setStatus("uploading");
    try {
      const result = await ingestText(textContent, textSource, category);
      setStatus("success");
      setMessage(`✓ ${result.chunks} chunk teks berhasil diingest.`);
      setTextContent("");
    } catch (e) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Ingest gagal.");
    }
  }, [textContent, textSource, category]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-300">Upload Basis Pengetahuan</h3>
        <div className="flex gap-2">
          <button
            onClick={() => setTextMode(false)}
            className={clsx("px-3 py-1 rounded-lg text-xs font-medium transition-colors",
              !textMode ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-400 hover:text-slate-200"
            )}
          >
            PDF
          </button>
          <button
            onClick={() => setTextMode(true)}
            className={clsx("px-3 py-1 rounded-lg text-xs font-medium transition-colors",
              textMode ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-400 hover:text-slate-200"
            )}
          >
            Teks
          </button>
        </div>
      </div>

      {/* Category selector */}
      <select
        value={category}
        onChange={(e) => setCategory(e.target.value)}
        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
      >
        <option value="faq">FAQ Umum</option>
        <option value="produk">Produk</option>
        <option value="pengiriman">Pengiriman</option>
        <option value="billing">Tagihan</option>
        <option value="teknis">Teknis</option>
      </select>

      {!textMode ? (
        /* Drop zone */
        <div
          className={clsx(
            "border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer",
            isDragging
              ? "border-blue-500 bg-blue-500/10"
              : "border-slate-600 hover:border-slate-500",
          )}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
          }}
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
          {status === "uploading" ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-400 text-sm">Mengupload & memproses...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-slate-500" />
              <p className="text-slate-300 text-sm font-medium">Seret PDF ke sini atau klik untuk browse</p>
              <p className="text-slate-500 text-xs">Maks. 50 MB</p>
            </div>
          )}
        </div>
      ) : (
        /* Text input */
        <div className="space-y-2">
          <input
            value={textSource}
            onChange={(e) => setTextSource(e.target.value)}
            placeholder="Sumber (misal: manual, website)"
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <textarea
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            rows={6}
            placeholder="Paste konten FAQ atau pengetahuan di sini..."
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
          />
          <button
            onClick={handleTextSubmit}
            disabled={!textContent.trim() || status === "uploading"}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
          >
            {status === "uploading" ? "Memproses..." : "Simpan ke Basis Pengetahuan"}
          </button>
        </div>
      )}

      {/* Status message */}
      {message && (
        <div className={clsx(
          "flex items-start gap-2 p-3 rounded-lg text-sm animate-fade-in",
          status === "success"
            ? "bg-green-900/30 border border-green-700 text-green-300"
            : "bg-red-900/30 border border-red-700 text-red-300",
        )}>
          {status === "success"
            ? <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            : <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          }
          {message}
        </div>
      )}
    </div>
  );
}
