import { useState, useCallback } from 'react';
import UploadZone from './components/UploadZone';
import ResultPanel from './components/ResultPanel';

const API_URL = import.meta.env.DEV
  ? 'http://localhost:8000'
  : '';

const STATES = {
  IDLE: 'idle',
  PREVIEW: 'preview',
  PROCESSING: 'processing',
  DONE: 'done',
  ERROR: 'error',
};

const PROCESSING_STEPS = [
  '🔍 Analyzing your flowchart...',
  '🤖 Qwen2.5-VL is reading shapes & text...',
  '📐 Detecting connections & arrows...',
  '🔧 Building Excalidraw elements...',
  '✨ Almost there...',
];

export default function App() {
  const [state, setState] = useState(STATES.IDLE);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [processingStep, setProcessingStep] = useState(0);
  const [previewFailed, setPreviewFailed] = useState(false);

  const handleFileSelected = useCallback((selectedFile) => {
    // Validate type
    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/bmp'];
    if (!validTypes.includes(selectedFile.type)) {
      setError('Please upload a JPG, PNG, or WebP image.');
      setState(STATES.ERROR);
      return;
    }

    // Validate size (20MB)
    if (selectedFile.size > 20 * 1024 * 1024) {
      setError('Image is too large. Maximum size is 20MB.');
      setState(STATES.ERROR);
      return;
    }

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setPreviewFailed(false);
    setState(STATES.PREVIEW);
  }, []);

  const handleConvert = useCallback(async () => {
    if (!file) return;

    setState(STATES.PROCESSING);
    setProcessingStep(0);

    // Cycle through processing steps for UX
    const stepInterval = setInterval(() => {
      setProcessingStep((prev) =>
        prev < PROCESSING_STEPS.length - 1 ? prev + 1 : prev
      );
    }, 3000);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_URL}/api/convert`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(stepInterval);

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${response.status})`);
      }

      const data = await response.json();

      if (data.success) {
        setResult(data);
        setState(STATES.DONE);
      } else {
        throw new Error('Conversion failed. Please try again.');
      }
    } catch (err) {
      clearInterval(stepInterval);
      setError(err.message || 'Something went wrong. Please try again.');
      setState(STATES.ERROR);
    }
  }, [file]);

  const handleReset = useCallback(() => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setResult(null);
    setError('');
    setState(STATES.IDLE);
  }, [preview]);

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-logo">✏️</div>
        <h1 className="app-title">Hand2Excal</h1>
        <p className="app-subtitle">
          Transform your handwritten flowcharts into editable Excalidraw
          diagrams powered by AI
        </p>
      </header>

      <main className="app-main">
        {/* IDLE — Show upload zone */}
        {state === STATES.IDLE && (
          <UploadZone onFileSelected={handleFileSelected} />
        )}

        {/* PREVIEW — Show image preview + convert button */}
        {state === STATES.PREVIEW && file && (
          <div className="preview-container">
            <UploadZone onFileSelected={handleFileSelected} />
            <div className="preview-card" style={{ marginTop: '1rem' }}>
              {previewFailed ? (
                <div className="preview-thumbnail preview-fallback">🖼️</div>
              ) : (
                <img
                  src={preview}
                  alt="Flowchart preview"
                  className="preview-thumbnail"
                  onError={() => setPreviewFailed(true)}
                />
              )}
              <div className="preview-info">
                <p className="preview-name">{file.name}</p>
                <p className="preview-size">{formatFileSize(file.size)}</p>
              </div>
              <div className="preview-actions">
                <button className="btn-convert" onClick={handleConvert}>
                  🚀 Convert
                </button>
                <button
                  className="btn-clear"
                  onClick={handleReset}
                  title="Remove"
                >
                  ✕
                </button>
              </div>
            </div>
          </div>
        )}

        {/* PROCESSING — Show spinner + steps */}
        {state === STATES.PROCESSING && (
          <div className="processing-container">
            <div className="processing-card">
              <div className="processing-spinner" />
              <h3 className="processing-title">Converting your flowchart</h3>
              <p className="processing-step">
                {PROCESSING_STEPS[processingStep]}
              </p>
            </div>
          </div>
        )}

        {/* DONE — Show result panel */}
        {state === STATES.DONE && result && (
          <ResultPanel result={result} onReset={handleReset} />
        )}

        {/* ERROR — Show error message */}
        {state === STATES.ERROR && (
          <div className="error-container">
            <div className="error-card">
              <div className="error-icon">😔</div>
              <h3 className="error-title">Conversion Failed</h3>
              <p className="error-message">{error}</p>
              <button className="btn-retry" onClick={handleReset}>
                🔄 Try Again
              </button>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        Powered by{' '}
        <a
          href="https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct"
          target="_blank"
          rel="noopener"
        >
          Qwen2.5-VL
        </a>{' '}
        ·{' '}
        <a href="https://excalidraw.com" target="_blank" rel="noopener">
          Excalidraw
        </a>
      </footer>
    </div>
  );
}
