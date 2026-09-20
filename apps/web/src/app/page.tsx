
"use client";

import { useEffect, useRef, useState } from "react";

type AnalysisResponse = {
  data: {
    analysis_id: string;
    session_id: string;
    status: string;
    observations: Array<{
      observation_id: string;
      object_class: string;
      confidence: number;
      spatial?: {
        horizontal?: string;
        vertical?: string;
        relative_proximity?: string;
      };
    }>;
    events: Array<{
      event_id: string;
      event_type: string;
      object_class: string;
      direction?: string;
      movement?: string;
      confidence: number;
    }>;
    risk_assessment: {
      priority: string;
      risk_type: string;
      confidence: number;
      reason: string;
      requires_interruption: boolean;
    } | null;
    narration: {
      text: string;
      language: string;
      priority: string;
      validated: boolean;
    } | null;
    audio: {
      audio_url: string | null;
      status: string;
      language: string;
      voice: string;
    } | null;
    error_message: string | null;
  };
  request_id: string;
  timestamp: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000/api/v1";

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [speaking, setSpeaking] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
      window.speechSynthesis?.cancel();
    };
  }, [preview]);

  function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) return;

    if (!selectedFile.type.startsWith("image/")) {
      setError("Please select an image file.");
      return;
    }

    if (preview) URL.revokeObjectURL(preview);

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setResult(null);
    setError("");
  }

  async function handleAnalyze() {
    if (!file) {
      setError("Please upload an image first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    window.speechSynthesis?.cancel();
    setSpeaking(false);

    try {
      // Create a fresh session.
      const sessionResponse = await fetch(
        `${API_BASE}/sessions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer dev-user",
          },
          body: JSON.stringify({
            mode: "assist",
          }),
        }
      );

      if (!sessionResponse.ok) {
        throw new Error(
          `Session creation failed (${sessionResponse.status})`
        );
      }

      const sessionJson = await sessionResponse.json();
      const sessionId = sessionJson.data?.session_id;

      if (!sessionId) {
        throw new Error("The API did not return a session ID.");
      }

      // Upload the image using the API's expected field name.
      const formData = new FormData();
      formData.append("image", file);

      const analysisResponse = await fetch(
        `${API_BASE}/sessions/${sessionId}/analysis`,
        {
          method: "POST",
          headers: {
            Authorization: "Bearer dev-user",
          },
          body: formData,
        }
      );

      const analysisJson = await analysisResponse.json();

      if (!analysisResponse.ok) {
        throw new Error(
          analysisJson.detail
            ? JSON.stringify(analysisJson.detail)
            : `Analysis failed (${analysisResponse.status})`
        );
      }

      if (!analysisJson.data) {
        throw new Error("The API returned an unexpected response.");
      }

      setResult(analysisJson as AnalysisResponse);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  }

  function speakNarration() {
    const narration = result?.data.narration;

    if (!narration?.text) {
      setError("No narration is available to speak.");
      return;
    }

    if (!("speechSynthesis" in window)) {
      setError("Speech synthesis is not supported in this browser.");
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(
      narration.text
    );

    utterance.lang = narration.language || "en-IN";
    utterance.rate = 1;

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => {
      setSpeaking(false);
      setError("Browser speech could not be played.");
    };

    window.speechSynthesis.speak(utterance);
  }

  function stopNarration() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setSpeaking(false);
  }

  const analysis = result?.data;
  const risk = analysis?.risk_assessment;
  const narration = analysis?.narration;
  const audio = analysis?.audio;

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-5xl px-5 py-10">
        <header className="mb-10">
          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
            SightSense
          </p>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            See the world through sound.
          </h1>

          <p className="mt-4 max-w-2xl text-slate-300">
            Upload a scene image to test the assistance
            analysis pipeline and hear its narration.
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Image upload */}
          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">
              1. Upload a scene
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              Choose an image from your device.
            </p>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="mt-5 block w-full text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-cyan-500 file:px-4 file:py-2 file:font-semibold file:text-slate-950 hover:file:bg-cyan-400"
            />

            {preview && (
              <div className="mt-5 overflow-hidden rounded-xl border border-slate-700">
                <img
                  src={preview}
                  alt="Selected scene preview"
                  className="max-h-80 w-full object-contain"
                />
              </div>
            )}

            {file && (
              <p className="mt-3 break-all text-xs text-slate-400">
                Selected: {file.name}
              </p>
            )}

            <button
              type="button"
              onClick={handleAnalyze}
              disabled={!file || loading}
              className="mt-6 w-full rounded-xl bg-cyan-400 px-5 py-3 font-bold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Analyzing..." : "Analyze image"}
            </button>

            {loading && (
              <p className="mt-3 text-center text-sm text-slate-400">
                Sending image to SightSense...
              </p>
            )}
          </section>

          {/* Results */}
          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">
              2. Scene insights
            </h2>

            {!analysis && !loading && (
              <div className="mt-5 rounded-xl border border-dashed border-slate-700 p-6 text-center text-slate-400">
                Your analysis will appear here.
              </div>
            )}

            {loading && (
              <div className="mt-5 rounded-xl bg-slate-800 p-6 text-slate-300">
                <p className="animate-pulse">
                  Processing your image...
                </p>
              </div>
            )}

            {analysis && (
              <div className="mt-5 space-y-5">
                <div className="rounded-xl bg-slate-800 p-4">
                  <p className="text-xs uppercase tracking-wider text-slate-400">
                    Analysis status
                  </p>
                  <p className="mt-1 font-semibold text-emerald-400">
                    {analysis.status}
                  </p>
                </div>

                {/* Risk assessment */}
                <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-amber-300">
                    Risk assessment
                  </p>

                  {risk ? (
                    <>
                      <p className="mt-2 text-lg font-bold">
                        {risk.priority.toUpperCase()}{" "}
                        · {risk.risk_type.replaceAll("_", " ")}
                      </p>

                      <p className="mt-2 text-sm text-slate-200">
                        {risk.reason}
                      </p>

                      {risk.requires_interruption && (
                        <p className="mt-3 text-sm font-semibold text-amber-300">
                          Immediate attention requested by the analysis.
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="mt-2 text-slate-300">
                      No risk assessment returned.
                    </p>
                  )}
                </div>

                {/* Narration */}
                <div className="rounded-xl bg-slate-800 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-cyan-300">
                    Narration
                  </p>

                  <p className="mt-3 text-lg leading-relaxed">
                    {narration?.text ||
                      "No narration returned."}
                  </p>

                  {narration && (
                    <p className="mt-2 text-xs text-slate-400">
                      Language: {narration.language} ·{" "}
                      {narration.validated
                        ? "Validated"
                        : "Not validated"}
                    </p>
                  )}

                  <div className="mt-5 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={speakNarration}
                      disabled={!narration?.text || speaking}
                      className="rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
                    >
                      {speaking
                        ? "Speaking..."
                        : "🔊 Speak narration"}
                    </button>

                    <button
                      type="button"
                      onClick={stopNarration}
                      disabled={!speaking}
                      className="rounded-lg border border-slate-600 px-4 py-2 font-semibold hover:bg-slate-700 disabled:opacity-50"
                    >
                      ⏹ Stop
                    </button>
                  </div>
                </div>

                {/* Audio status */}
                <div className="rounded-xl border border-slate-700 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Generated audio
                  </p>

                  {audio?.audio_url ? (
                    <audio
                      controls
                      className="mt-3 w-full"
                      src={audio.audio_url}
                    >
                      Your browser does not support audio playback.
                    </audio>
                  ) : (
                    <p className="mt-2 text-sm text-slate-300">
                      {audio?.status === "pending"
                        ? "Generated audio is pending. Use Speak narration for browser speech."
                        : "No generated audio file is available. Use browser speech instead."}
                    </p>
                  )}
                </div>

                {/* Observations */}
                <div className="rounded-xl bg-slate-800 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Detected observations
                  </p>

                  {analysis.observations.length > 0 ? (
                    <ul className="mt-3 space-y-2">
                      {analysis.observations.map((item) => (
                        <li
                          key={item.observation_id}
                          className="flex items-center justify-between gap-3 text-sm"
                        >
                          <span className="capitalize">
                            {item.object_class.replaceAll("_", " ")}
                          </span>
                          <span className="text-slate-400">
                            {(item.confidence * 100).toFixed(0)}%
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-slate-400">
                      No observations returned.
                    </p>
                  )}
                </div>

                <p className="text-xs leading-relaxed text-slate-500">
                  Development note: verify detections against the
                  actual image. Mock or unverified outputs must not
                  be relied on for navigation or safety decisions.
                </p>
              </div>
            )}
          </section>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200"
          >
            {error}
          </div>
        )}

        <footer className="mt-10 border-t border-slate-800 pt-5 text-xs text-slate-500">
          SightSense · Development interface
        </footer>
      </div>
    </main>
  );
}