import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface DragDropAreaProps {
  onFilesAccepted: (files: File[]) => void;
}

const DragDropArea: React.FC<DragDropAreaProps> = ({ onFilesAccepted }) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFilesAccepted(acceptedFiles);
  }, [onFilesAccepted]);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxFiles: 1,
    multiple: false
  });

  return (
    <div
      {...getRootProps()}
      className={`drag-drop-area ${
        isDragActive
          ? 'drag-drop-area-active'
          : isDragReject
          ? 'drag-drop-area-reject'
          : ''
      }`}
      role="button"
      tabIndex={0}
      aria-label="Upload invoice file"
    >
      <input {...getInputProps()} aria-label="File input" />
      <div className="drag-drop-content">
        <svg
          className="drag-drop-icon"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        {isDragActive ? (
          <p className="drag-drop-title">Drop the invoice here</p>
        ) : isDragReject ? (
          <p className="drag-drop-title drag-drop-reject-text">Only PDF and image files are accepted</p>
        ) : (
          <>
            <p className="drag-drop-title">
              Drag & drop an invoice here
            </p>
            <p className="drag-drop-subtitle">or click to browse files</p>
            <p className="drag-drop-help">
              Supported formats: PDF, JPG, JPEG, PNG
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default DragDropArea;
