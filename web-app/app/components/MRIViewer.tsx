"use client";

import { Region } from "../types";
import { useState } from "react";

interface MRIViewerProps {
  imageSrc: string;
  regions: Region[];
  highlightedRegion: number[] | null;
  onRegionClick: (regionNumbers: number[] | null) => void;
}

export default function MRIViewer({
  imageSrc,
  regions,
  highlightedRegion,
  onRegionClick,
}: MRIViewerProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({
    width: 0,
    height: 0,
  });

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageDimensions({
      width: img.naturalWidth,
      height: img.naturalHeight,
    });
    setImageLoaded(true);
  };

  return (
    <div className="border border-border rounded-lg bg-card p-6 h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-mono font-semibold">MRI Visualization</h2>
      </div>

      <div className="relative bg-background rounded border border-border overflow-hidden">
        {/* Original MRI Image (grayscale, no colors) */}
        <img
          src={imageSrc}
          alt="MRI scan"
          className="w-full h-auto block"
          onLoad={handleImageLoad}
        />

        {/* Rectangle overlay for highlighted regions */}
        {imageLoaded &&
          highlightedRegion !== null &&
          highlightedRegion.length > 0 &&
          imageDimensions.width > 0 && (
            <div className="absolute inset-0 pointer-events-none">
              {regions
                .filter((r) => highlightedRegion.includes(r.number))
                .map((region) => {
                  const [r, g, b] = region.color;
                  // Use actual image dimensions for correct positioning
                  const left = (region.bbox[0] / imageDimensions.width) * 100;
                  const top = (region.bbox[1] / imageDimensions.height) * 100;
                  const width =
                    ((region.bbox[2] - region.bbox[0]) /
                      imageDimensions.width) *
                    100;
                  const height =
                    ((region.bbox[3] - region.bbox[1]) /
                      imageDimensions.height) *
                    100;

                  return (
                    <div
                      key={region.id}
                      className="absolute"
                      style={{
                        left: `${left}%`,
                        top: `${top}%`,
                        width: `${width}%`,
                        height: `${height}%`,
                        backgroundColor: `rgba(236, 72, 153, 0.3)`,
                        border: `3px solid rgb(236, 72, 153)`,
                        borderRadius: "4px",
                        boxShadow: `0 0 20px rgba(236, 72, 153, 0.8)`,
                      }}
                    />
                  );
                })}
            </div>
          )}
      </div>

      {/* Region Legend */}
      <div className="mt-4 space-y-2 max-h-48 overflow-y-auto">
        <div className="text-xs font-mono text-muted-foreground mb-2">
          {regions.length} regions identified
        </div>
        {regions
          .filter((r) => r.mentioned)
          .map((region) => {
            const [r, g, b] = region.color;
            return (
              <div
                key={region.id}
                className="flex items-center gap-2 text-xs font-mono cursor-pointer hover:bg-muted p-1 rounded transition-colors"
                onMouseEnter={() => onRegionClick([region.number])}
                onMouseLeave={() => onRegionClick(null)}
              >
                <span className="text-muted-foreground">
                  Region {region.number}:
                </span>
                <span className="text-foreground capitalize">
                  {region.label}
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
}
