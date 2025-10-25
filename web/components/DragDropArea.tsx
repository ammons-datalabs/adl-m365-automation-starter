
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface DragDropAreaProps {
  onFilesAccepted: (files: File[]) => void;
}

const DragDropArea: React.FC<DragDropAreaProps> = ({ onFilesAccepted }) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFilesAccepted(acceptedFiles);
  }, [onFilesAccepted]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed p-8 text-center cursor-pointer ${
        isDragActive ? 'border-blue-500 bg-blue-100' : 'border-gray-300 bg-gray-50'
      }`}
    >
      <input {...getInputProps()} />
      {isDragActive ? (
        <p>Drop the files here ...</p>
      ) : (
        <p>Drag 'n' drop some files here, or click to select files</p>
      )}
    </div>
  );
};

export default DragDropArea;
