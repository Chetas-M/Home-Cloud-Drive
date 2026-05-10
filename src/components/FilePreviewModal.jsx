import React, { useEffect, useState, useRef } from "react";
import { X, Download, ChevronLeft, ChevronRight } from "lucide-react";
import api from "../api";

export default function FilePreviewModal({
    file,
    files,
    onClose,
    onDownload,
    onNavigate,
}) {
    const [textContent, setTextContent] = useState(null);
    const [textLoading, setTextLoading] = useState(false);
    const [previewUrl, setPreviewUrl] = useState(null);

    // Touch swipe state
    const touchStartRef = useRef(null);
    const touchDeltaRef = useRef(0);
    const contentRef = useRef(null);

    // Fetch text content when previewing text files
    useEffect(() => {
        if (file.type === "text" && !file.blob) {
            setTextLoading(true);
            setTextContent(null);
            api.downloadFile(file.id)
                .then(blob => blob.text())
                .then(text => {
                    // Limit display to ~100KB to prevent browser freeze
                    setTextContent(text.length > 102400 ? text.slice(0, 102400) + "\n\n... (truncated)" : text);
                })
                .catch(() => setTextContent("Failed to load file content."))
                .finally(() => setTextLoading(false));
        } else {
            setTextContent(null);
        }
    }, [file]);

    // Fetch blob URL for image/video/PDF previews (avoids JWT in URL)
    useEffect(() => {
        if (["image", "video", "pdf"].includes(file.type)) {
            let active = true;
            let objectUrl = null;
            setPreviewUrl(null);
            api.fetchPreviewBlob(file.id)
                .then(url => {
                    objectUrl = url;
                    if (active) {
                        setPreviewUrl(url);
                    } else {
                        URL.revokeObjectURL(url);
                    }
                })
                .catch(() => {
                    if (active) {
                        setPreviewUrl(null);
                    }
                });
            return () => {
                active = false;
                if (objectUrl) URL.revokeObjectURL(objectUrl);
            };
        }
        setPreviewUrl(null);
    }, [file]);

    // Keyboard navigation
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === "Escape") onClose();
            if (e.key === "ArrowLeft") onNavigate?.("prev");
            if (e.key === "ArrowRight") onNavigate?.("next");
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [onClose, onNavigate]);

    // Touch swipe handlers for mobile navigation
    const handleTouchStart = (e) => {
        if (!onNavigate) return;
        const touch = e.touches[0];
        touchStartRef.current = { x: touch.clientX, y: touch.clientY, time: Date.now() };
        touchDeltaRef.current = 0;
    };

    const handleTouchMove = (e) => {
        if (!touchStartRef.current || !onNavigate) return;
        const touch = e.touches[0];
        const dx = touch.clientX - touchStartRef.current.x;
        const dy = touch.clientY - touchStartRef.current.y;

        // Only track horizontal swipes (prevent vertical scroll interference)
        if (Math.abs(dx) > Math.abs(dy) * 1.5) {
            e.preventDefault();
            touchDeltaRef.current = dx;
        }
    };

    const handleTouchEnd = () => {
        if (!touchStartRef.current || !onNavigate) return;
        const dx = touchDeltaRef.current;
        const elapsed = Date.now() - touchStartRef.current.time;

        // Swipe threshold: 60px or fast swipe (100px/s)
        const isSwipe = Math.abs(dx) > 60 || (Math.abs(dx) > 30 && elapsed < 300);

        if (isSwipe) {
            if (dx > 0) {
                onNavigate("prev");
            } else {
                onNavigate("next");
            }
        }

        touchStartRef.current = null;
        touchDeltaRef.current = 0;
    };

    const renderContent = () => {
        // Text files: fetch content and display in <pre>
        if (file.type === "text") {
            if (textLoading) {
                return (
                    <div className="preview-placeholder">
                        <p>Loading file content...</p>
                    </div>
                );
            }
            if (textContent !== null) {
                return (
                    <pre className="preview-text-content">{textContent}</pre>
                );
            }
        }

        // Image, video, PDF: use fetched blob URL
        if (!previewUrl) {
            return (
                <div className="preview-placeholder">
                    <p>Loading preview...</p>
                </div>
            );
        }

        if (file.type === "image") {
            return <img src={previewUrl} alt={file.name} className="preview-image" />;
        }

        if (file.type === "video") {
            return (
                <video src={previewUrl} controls autoPlay className="preview-video">
                    Your browser does not support video playback.
                </video>
            );
        }

        if (file.type === "pdf") {
            return (
                <iframe
                    src={previewUrl}
                    title={file.name}
                    className="preview-pdf"
                />
            );
        }

        return (
            <div className="preview-placeholder">
                <p>Cannot preview this file type</p>
                <p className="text-muted">Click Download to view it</p>
            </div>
        );
    };

    return (
        <div className="preview-modal-overlay" onClick={onClose}>
            <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="preview-header">
                    <h3 className="preview-title">{file.name}</h3>
                    <div className="preview-actions">
                        <button
                            className="preview-btn"
                            onClick={() => onDownload(file)}
                            title="Download"
                        >
                            <Download size={20} />
                        </button>
                        <button className="preview-btn" onClick={onClose} title="Close">
                            <X size={20} />
                        </button>
                    </div>
                </div>

                {/* Content with touch swipe support */}
                <div
                    className="preview-content"
                    ref={contentRef}
                    onTouchStart={handleTouchStart}
                    onTouchMove={handleTouchMove}
                    onTouchEnd={handleTouchEnd}
                >
                    {onNavigate && (
                        <button
                            className="preview-nav prev"
                            onClick={() => onNavigate("prev")}
                        >
                            <ChevronLeft size={32} />
                        </button>
                    )}

                    {renderContent()}

                    {onNavigate && (
                        <button
                            className="preview-nav next"
                            onClick={() => onNavigate("next")}
                        >
                            <ChevronRight size={32} />
                        </button>
                    )}
                </div>

                {/* Mobile swipe hint */}
                {onNavigate && files && files.length > 1 && (
                    <div className="preview-swipe-hint">
                        Swipe to navigate • {files.findIndex(f => f.id === file.id) + 1} of {files.length}
                    </div>
                )}
            </div>
        </div>
    );
}
