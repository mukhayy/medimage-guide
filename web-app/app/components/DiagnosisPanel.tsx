"use client";

import { Region } from "../types";
import { useMemo } from "react";

interface DiagnosisPanelProps {
  diagnosis: string;
  regions: Region[];
  onTermHover: (regionNumbers: number[] | null) => void;
}

export default function DiagnosisPanel({
  diagnosis,
  regions,
  onTermHover,
}: DiagnosisPanelProps) {
  // Create a map of anatomical terms to regions (supporting category matches)
  const termToRegions = useMemo(() => {
    const map = new Map<string, Region[]>();

    regions.forEach((region) => {
      if (region.mentioned) {
        const label = region.label.toLowerCase();

        // Add exact match
        if (!map.has(label)) {
          map.set(label, []);
        }
        map.get(label)!.push(region);

        // Add category matches
        if (label.includes("cuneiform")) {
          if (!map.has("cuneiforms")) {
            map.set("cuneiforms", []);
          }
          map.get("cuneiforms")!.push(region);
        }
        if (label.includes("metatarsal")) {
          if (!map.has("metatarsals")) {
            map.set("metatarsals", []);
          }
          map.get("metatarsals")!.push(region);
        }
        if (label.includes("phalanx")) {
          if (!map.has("phalanges")) {
            map.set("phalanges", []);
          }
          map.get("phalanges")!.push(region);
        }
        if (label.includes("tendon")) {
          if (!map.has("tendons")) {
            map.set("tendons", []);
          }
          map.get("tendons")!.push(region);
        }
        if (label.includes("ligament")) {
          if (!map.has("ligaments")) {
            map.set("ligaments", []);
          }
          map.get("ligaments")!.push(region);
        }
        if (label.includes("joint")) {
          if (!map.has("joints")) {
            map.set("joints", []);
          }
          map.get("joints")!.push(region);
        }
      }
    });
    return map;
  }, [regions]);

  // Parse diagnosis text and wrap anatomical terms
  const parseAndHighlight = (text: string) => {
    const parts: JSX.Element[] = [];
    let lastIndex = 0;
    const textLower = text.toLowerCase();

    // Sort terms by length (longest first) to avoid partial matches
    const sortedTerms = Array.from(termToRegions.keys()).sort(
      (a, b) => b.length - a.length,
    );

    // Find all occurrences of anatomical terms
    const matches: Array<{ start: number; end: number; term: string }> = [];

    sortedTerms.forEach((term) => {
      // Use word boundaries to find whole word matches
      const regex = new RegExp(`\\b${term}\\b`, "gi");
      let match;

      while ((match = regex.exec(text)) !== null) {
        // Check if this match overlaps with existing matches
        const overlaps = matches.some(
          (m) =>
            (match!.index >= m.start && match!.index < m.end) ||
            (match!.index + term.length > m.start &&
              match!.index + term.length <= m.end),
        );

        if (!overlaps) {
          matches.push({
            start: match.index,
            end: match.index + term.length,
            term: term,
          });
        }
      }
    });

    // Sort matches by position
    matches.sort((a, b) => a.start - b.start);

    // Build the highlighted text
    matches.forEach((match, idx) => {
      // Add text before the match
      if (match.start > lastIndex) {
        parts.push(
          <span key={`text-${idx}`}>
            {text.substring(lastIndex, match.start)}
          </span>,
        );
      }

      // Add the highlighted term
      const matchedRegions = termToRegions.get(match.term)!;
      // Use first region's color for consistency
      const [r, g, b] = matchedRegions[0].color;

      parts.push(
        <span
          key={`term-${idx}`}
          className="anatomical-term cursor-pointer font-semibold transition-all"
          style={{
            color: `rgb(236, 72, 153)`, // Pink for all
            textDecoration: "underline",
            textDecorationColor: `rgba(236, 72, 153, 0.3)`,
            textUnderlineOffset: "2px",
          }}
          onMouseEnter={() => onTermHover(matchedRegions.map((r) => r.number))}
          onMouseLeave={() => onTermHover(null)}
          title={
            matchedRegions.length === 1
              ? `Region ${matchedRegions[0].number}: ${matchedRegions[0].label}`
              : `${matchedRegions.length} regions: ${matchedRegions.map((r) => r.label).join(", ")}`
          }
        >
          {text.substring(match.start, match.end)}
        </span>,
      );

      lastIndex = match.end;
    });

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(<span key="text-final">{text.substring(lastIndex)}</span>);
    }

    return parts;
  };

  // Split diagnosis into sections
  const sections = useMemo(() => {
    const lines = diagnosis.split("\n");
    const result: Array<{ title: string; content: string }> = [];
    let currentSection: { title: string; content: string } | null = null;

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) return;

      // Check if this is a section header
      if (
        trimmed.match(/^(FINDINGS|IMPRESSION|RECOMMENDATIONS):?$/i) ||
        trimmed.match(/^\d+\.\s/)
      ) {
        if (currentSection) {
          result.push(currentSection);
        }
        currentSection = { title: trimmed.replace(":", ""), content: "" };
      } else {
        if (currentSection) {
          currentSection.content +=
            (currentSection.content ? " " : "") + trimmed;
        } else {
          // Content before any header
          currentSection = { title: "", content: trimmed };
        }
      }
    });

    if (currentSection) {
      result.push(currentSection);
    }

    return result;
  }, [diagnosis]);

  return (
    <div className="border border-border rounded-lg bg-card p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-mono font-semibold">Diagnostic Report</h2>
        <div className="text-xs font-mono text-muted-foreground">
          Hover terms to highlight
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 text-sm font-mono leading-relaxed">
        {sections.map((section, idx) => (
          <div key={idx}>
            {section.title && (
              <h3 className="font-semibold text-foreground mb-2 text-base">
                {section.title}
              </h3>
            )}
            <p className="text-muted-foreground whitespace-pre-wrap">
              {parseAndHighlight(section.content)}
            </p>
          </div>
        ))}
      </div>

      {/* Instructions */}
      <div className="mt-4 pt-4 border-t border-border">
        <div className="text-xs font-mono text-muted-foreground space-y-1">
          <p> AI can make mistakes, consult with you radiologist</p>
        </div>
      </div>
    </div>
  );
}
