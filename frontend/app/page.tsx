"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";

type ElementFeature = {
  element_type: string;
  x: number;
  y: number;
  width: number;
  height: number;
};

type Match = {
  template_id: string;
  name: string;
  similarity: number;
  preview_url: string | null;
  download_url: string;
  is_fallback: boolean;
};

type UploadResult = {
  presentation_id: string;
  analysis: {
    filename: string;
    slide_count: number;
    slides: Array<{
      slide_number: number;
      elements: ElementFeature[];
      structural_description: string;
      preview_url: string | null;
    }>;
  };
  matches: Record<string, Match[]>;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const ASSET_URL = API_URL.replace(/\/api\/?$/, "");

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Record<number, Match>>({});
  const resultsRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (result) {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setResult(null);
    setSelected({});
    setError(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${API_URL}/presentations/analyze`, {
        method: "POST",
        body,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Upload failed.");
      setResult(payload);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10 md:py-16">
      <nav className="mb-16 flex items-center justify-between">
        <div className="flex items-center gap-3 font-semibold">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-ink text-white">B</span>
          Beautify Slides
        </div>
        <span className="rounded-full border border-slate-200 bg-white/70 px-4 py-2 text-xs font-medium text-slate-500">
          Privacy-first demo
        </span>
      </nav>

      <section className="grid items-start gap-10 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="pt-4">
          <p className="mb-5 text-sm font-semibold uppercase tracking-[0.2em] text-accent">
            Structural slide retrieval
          </p>
          <h1 className="max-w-2xl text-5xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
            Better slide ideas, without reading your words.
          </h1>
          <p className="mt-7 max-w-xl text-lg leading-8 text-slate-600">
            Upload a PowerPoint. We compare its layout, spacing, typography, colors, and element
            geometry with a library of polished reference slides.
          </p>
          <div className="mt-9 flex flex-wrap gap-5 text-sm text-slate-500">
            <span>✓ Raw text excluded</span>
            <span>✓ Local embeddings</span>
            <span>✓ PPTX only</span>
          </div>
        </div>

        <form onSubmit={submit} className="rounded-[2rem] border border-white bg-white/85 p-7 shadow-soft backdrop-blur md:p-9">
          <div className="mb-7">
            <h2 className="text-xl font-semibold">Analyze a presentation</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">Choose an ugly sample deck up to 25 MB.</p>
          </div>
          <label className="flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-mist/70 p-8 text-center transition hover:border-accent/50 hover:bg-violet-50">
            <span className="mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-white text-2xl shadow-sm">↑</span>
            <span className="font-medium">{file ? file.name : "Drop a PPTX here or click to browse"}</span>
            <span className="mt-2 text-xs text-slate-400">PowerPoint .pptx</span>
            <input className="sr-only" type="file" accept=".pptx" onChange={chooseFile} />
          </label>
          <button
            type="submit"
            disabled={!file || loading}
            className="mt-5 w-full rounded-xl bg-ink px-5 py-4 font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Analyzing structure…" : "Find better designs"}
          </button>
          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        </form>
      </section>

      {result && (
        <section ref={resultsRef} className="mt-16 scroll-mt-8 rounded-[2rem] bg-white p-7 shadow-soft md:p-10">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-100 pb-7">
            <div>
              <p className="text-sm text-slate-400">Analysis complete</p>
              <h2 className="mt-1 text-2xl font-semibold">{result.analysis.filename}</h2>
            </div>
            <span className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
              {result.analysis.slide_count} slide{result.analysis.slide_count === 1 ? "" : "s"}
            </span>
          </div>

          <div className="mt-8 grid gap-6">
            {result.analysis.slides.map((slide) => {
              const matches = result.matches[String(slide.slide_number)] ?? [];
              const selectedMatch = selected[slide.slide_number];
              return (
                <article
                  key={slide.slide_number}
                  className="grid gap-7 rounded-2xl border border-slate-200 p-6 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.85fr)]"
                >
                  <div className="flex items-center justify-between lg:col-span-2">
                    <h3 className="font-semibold">Slide {slide.slide_number}</h3>
                    <span className="text-xs text-slate-400">{slide.elements.length} elements</span>
                  </div>
                  <div>
                    {slide.preview_url ? (
                      <img
                        src={`${ASSET_URL}${slide.preview_url}`}
                        alt={`Uploaded slide ${slide.slide_number}`}
                        className="aspect-video w-full rounded-xl border border-slate-200 bg-white object-contain shadow-sm"
                      />
                    ) : (
                      <div className="relative aspect-video overflow-hidden rounded-xl bg-slate-50 ring-1 ring-slate-100">
                        {slide.elements.map((element, index) => (
                          <span
                            key={index}
                            title={element.element_type}
                            className="absolute rounded-sm border border-accent/40 bg-accent/10"
                            style={{
                              left: `${element.x * 100}%`,
                              top: `${element.y * 100}%`,
                              width: `${element.width * 100}%`,
                              height: `${element.height * 100}%`,
                            }}
                          />
                        ))}
                      </div>
                    )}
                    <p className="mt-5 whitespace-normal text-sm leading-6 text-slate-500">
                      {slide.structural_description}
                    </p>
                    <div className="mt-5 border-t border-slate-100 pt-4">
                      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
                        Recommended designs
                      </p>
                      {matches.length ? (
                        <div className="grid gap-4 sm:grid-cols-3">
                          {matches.map((match) => (
                            <button
                              key={match.template_id}
                              type="button"
                              onClick={() => setSelected((current) => ({ ...current, [slide.slide_number]: match }))}
                              className={`overflow-hidden rounded-xl border bg-white text-left transition ${
                                selectedMatch?.template_id === match.template_id
                                  ? "border-accent ring-2 ring-accent/20"
                                  : "border-slate-200 hover:border-accent/50"
                              }`}
                            >
                              {match.preview_url ? (
                                <img
                                  src={`${ASSET_URL}${match.preview_url}`}
                                  alt={`Preview of ${match.name}`}
                                  className="aspect-video w-full bg-slate-50 object-cover"
                                />
                              ) : (
                                <div className="grid aspect-video place-items-center bg-slate-50 text-xs text-slate-400">
                                  Preview unavailable
                                </div>
                              )}
                              <div className="p-3">
                                {match.is_fallback && (
                                  <span className="mb-2 inline-block rounded-full bg-amber-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                                    Closest fallback
                                  </span>
                                )}
                                <div className="flex items-start justify-between gap-2">
                                  <p className="line-clamp-2 text-xs font-medium leading-5 text-slate-700">{match.name}</p>
                                  <span className="shrink-0 text-xs font-semibold text-accent">
                                    {Math.round(match.similarity * 100)}%
                                  </span>
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-400">
                          No reference designs are indexed yet. Add reference slides and run ingestion.
                        </p>
                      )}
                    </div>
                  </div>

                  <aside className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5 lg:sticky lg:top-8 lg:self-start">
                    {selectedMatch ? (
                      <>
                        <div className="mb-4 flex items-start justify-between gap-4">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-accent">Selected design</p>
                            <h4 className="mt-1 text-sm font-semibold leading-6 text-slate-700">{selectedMatch.name}</h4>
                          </div>
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-accent shadow-sm">
                            {Math.round(selectedMatch.similarity * 100)}%
                          </span>
                        </div>
                        {selectedMatch.preview_url ? (
                          <img
                            src={`${ASSET_URL}${selectedMatch.preview_url}`}
                            alt={`Large preview of ${selectedMatch.name}`}
                            className="aspect-video w-full rounded-xl border border-slate-200 bg-white object-contain shadow-sm"
                          />
                        ) : (
                          <div className="grid aspect-video place-items-center rounded-xl bg-white text-sm text-slate-400">
                            Preview unavailable
                          </div>
                        )}
                      <a
                        href={`${ASSET_URL}${selectedMatch.download_url}`}
                        className="mt-4 block rounded-xl bg-ink px-4 py-3 text-center text-sm font-semibold text-white transition hover:bg-slate-700"
                      >
                        Download selected slide
                      </a>
                      </>
                    ) : (
                      <div className="grid min-h-72 place-items-center rounded-xl border-2 border-dashed border-slate-200 bg-white px-8 text-center">
                        <div>
                          <p className="font-medium text-slate-600">Select a recommended design</p>
                          <p className="mt-2 text-sm leading-6 text-slate-400">
                            Its larger preview and download button will appear here.
                          </p>
                        </div>
                      </div>
                    )}
                  </aside>
                </article>
              );
            })}
          </div>
        </section>
      )}
    </main>
  );
}
