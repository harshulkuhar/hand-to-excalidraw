import React, { useState } from 'react';

export default function TextInputZone({ onTextSubmit }) {
    const [text, setText] = useState('');

    const handleSubmit = () => {
        if (text.trim()) {
            onTextSubmit(text);
        }
    };

    return (
        <div className="upload-container">
            <div className="upload-card text-input-card">
                <label className="text-input-label" htmlFor="flowchart-text">
                    Paste your document or process flow description here:
                </label>
                <textarea
                    id="flowchart-text"
                    className="text-input-area"
                    placeholder="e.g. User logs in. If successful, show dashboard. Otherwise, show login error."
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    rows={10}
                />
                <button
                    className="btn-convert"
                    style={{ marginTop: '1rem', alignSelf: 'flex-start' }}
                    onClick={handleSubmit}
                    disabled={!text.trim()}
                >
                    🚀 Convert Text
                </button>
            </div>
        </div>
    );
}
