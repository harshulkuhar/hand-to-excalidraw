import { useState, useRef, useCallback } from 'react';

export default function UploadZone({ onFileSelected }) {
    const [dragging, setDragging] = useState(false);
    const fileInputRef = useRef(null);
    const dragCounter = useRef(0);

    const handleDragEnter = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter.current++;
        setDragging(true);
    }, []);

    const handleDragLeave = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter.current--;
        if (dragCounter.current === 0) {
            setDragging(false);
        }
    }, []);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragging(false);
        dragCounter.current = 0;

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            onFileSelected(files[0]);
        }
    }, [onFileSelected]);

    const handleClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileInput = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            onFileSelected(file);
        }
    };

    return (
        <div
            className={`upload-zone ${dragging ? 'dragging' : ''}`}
            onClick={handleClick}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
        >
            <span className="upload-icon">📸</span>
            <h2 className="upload-title">
                {dragging ? 'Drop your flowchart here!' : 'Upload your handwritten flowchart'}
            </h2>
            <p className="upload-description">
                Drag & drop a photo of your flowchart, or click to browse
            </p>
            <button className="upload-btn" onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                ✨ Choose Image
            </button>
            <p className="upload-formats">
                Supports JPG, PNG, WebP, HEIC • Max 20MB
            </p>
            <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/heic,image/bmp"
                onChange={handleFileInput}
                style={{ display: 'none' }}
            />
        </div>
    );
}
