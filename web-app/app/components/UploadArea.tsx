"use client";

import { useState, useRef } from "react";

interface UploadAreaProps {
  onUpload: (file: File) => void;
}

export default function UploadArea({ onUpload }: UploadAreaProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragging(true);
    } else if (e.type === "dragleave") {
      setIsDragging(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      handleFile(files[0]);
    }
  };

  const handleFile = (file: File) => {
    // Validate file type
    if (!file.type.startsWith("image/")) {
      alert("Please upload an image file");
      return;
    }

    onUpload(file);
  };

  return (
    <div className="border border-border rounded-lg bg-card p-6">
      <h2 className="text-base font-mono font-semibold mb-4">Upload MRI Scan</h2>

      {/* Drag & Drop Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer ${
          isDragging
            ? "border-foreground bg-muted"
            : "border-border hover:border-muted-foreground hover:bg-muted/50"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileInput}
          className="hidden"
        />

        <div className="space-y-4">
          <div className="text-4xl">📁</div>
          <div>
            <p className="text-sm font-mono text-foreground mb-1">
              Drop MRI scan here or click to browse
            </p>
            <p className="text-xs font-mono text-muted-foreground">
              Supports: PNG, JPG, DICOM
            </p>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="mt-4 p-4 bg-muted/50 rounded border border-border">
        <p className="text-xs font-mono text-muted-foreground">
          <strong className="text-foreground">Note:</strong> To analyze your own
          MRI, run the Python backend locally:{" "}
          <code className="bg-background px-1 py-0.5 rounded">
            python api.py
          </code>
        </p>
      </div>
    </div>
  );
}
