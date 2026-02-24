"use client";

import { useState } from "react";
import UploadArea from "./components/UploadArea";
import MRIViewer from "./components/MRIViewer";
import DiagnosisPanel from "./components/DiagnosisPanel";
import { MRIData } from "./types";

export default function Home() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [result, setResult] = useState<MRIData | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightedRegion, setHighlightedRegion] = useState<number[] | null>(
    null,
  );

  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    document.documentElement.classList.toggle("dark");
  };

  const loadDemo = async () => {
    try {
      // Fetch the actual demo data from the JSON file
      const response = await fetch("/demo/ankle/data.json");
      const data = await response.json();

      // Transform the data to match MRIData interface
      const mriData: MRIData = {
        visualization: "/demo/ankle/ankle.png",
        regions: data.regions.map((r: any) => ({
          id: r.id,
          number: r.number,
          label: r.label,
          mentioned: r.mentioned_in_diagnosis,
          color: r.color,
          bbox: r.bbox,
          center: r.center,
        })),
        diagnosis: data.diagnosis.full_report,
        metadata: {
          filename: data.image_info.filename,
          num_regions: data.image_info.num_regions,
          mentioned_regions: data.diagnosis.num_mentioned,
        },
      };

      setResult(mriData);
      setError(null);
    } catch (err: any) {
      setError("Failed to load demo data: " + err.message);
    }
  };

  const handleUpload = async (file: File) => {
    setAnalyzing(true);
    setError(null);
    setResult(null);

    try {
      // TODO: Connect to local Python backend
      // For now, simulate analysis
      await new Promise((resolve) => setTimeout(resolve, 1000));

      setError("Connect to local backend: python api.py on port 8000");
      // const formData = new FormData();
      // formData.append("image", file);
      // const response = await fetch("http://localhost:8000/analyze", {
      //   method: "POST",
      //   body: formData,
      // });
      // const data = await response.json();
      // setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleRegionHover = (regionNumbers: number[] | null) => {
    setHighlightedRegion(regionNumbers);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border px-6 py-5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight font-mono">
              MedImage Guide
            </h1>
            <p className="text-sm text-muted-foreground">
              AI-powered interactive MRI analysis. Powered with MedGemma and
              MedSAM2
            </p>
          </div>
          <div className="flex items-center gap-4">
            {!result && (
              <button
                onClick={loadDemo}
                className="px-4 py-2 text-sm font-mono text-muted-foreground hover:text-foreground border border-border rounded hover:bg-muted transition-colors"
              >
                Load Demo
              </button>
            )}
            <button
              onClick={toggleTheme}
              className="px-3 py-2 text-sm font-mono border border-border rounded hover:bg-muted transition-colors"
              title="Toggle theme"
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Upload Section */}
        {!result && !analyzing && <UploadArea onUpload={handleUpload} />}

        {/* Analyzing State */}
        {analyzing && (
          <div className="border border-border rounded-lg bg-card p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-foreground mb-4"></div>
            <p className="text-sm font-mono text-muted-foreground">
              Analyzing MRI scan...
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="border border-red-500/50 bg-red-500/10 rounded-lg p-4 mb-6">
            <p className="text-sm font-mono text-red-400">{error}</p>
          </div>
        )}

        {/* Results - Split View */}
        {result && (
          <div className="space-y-6">
            {/* Metadata Bar */}
            <div className="border border-border rounded-lg bg-card px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-6 text-sm font-mono">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Regions:</span>
                  <span className="text-foreground font-semibold">
                    {result.metadata.num_regions}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Mentioned:</span>
                  <span className="text-foreground font-semibold">
                    {result.metadata.mentioned_regions}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">File:</span>
                  <span className="text-foreground font-semibold">
                    {result.metadata.filename}
                  </span>
                </div>
              </div>
            </div>

            {/* Split View: MRI + Diagnosis */}
            <div className="grid grid-cols-2 gap-6">
              {/* Left: MRI Visualization */}
              <MRIViewer
                imageSrc={result.visualization}
                regions={result.regions}
                highlightedRegion={highlightedRegion}
                onRegionClick={handleRegionHover}
              />

              {/* Right: Diagnosis with Interactive Terms */}
              <DiagnosisPanel
                diagnosis={result.diagnosis}
                regions={result.regions}
                onTermHover={handleRegionHover}
              />
            </div>

            {/* New Analysis Button */}
            <div className="flex justify-center pt-4">
              <button
                onClick={() => {
                  setResult(null);
                  setError(null);
                  setHighlightedRegion(null);
                }}
                className="px-6 py-2 text-sm font-mono border border-border rounded hover:bg-muted transition-colors"
              >
                Analyze New MRI
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
