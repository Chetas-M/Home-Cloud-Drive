import React, { useState, useEffect } from "react";
import { Upload, X, CheckCircle, AlertCircle, Clock, Zap, WifiOff, RefreshCw, Wifi } from "lucide-react";

function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.max(0, Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatEta(seconds) {
    if (seconds <= 0) return "calculating...";
    if (seconds < 60) return `${seconds}s remaining`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s remaining`;
}

function formatSpeed(bytesPerSec) {
    if (bytesPerSec <= 0) return "--";
    return formatBytes(bytesPerSec) + "/s";
}

function StatusIcon({ status }) {
    switch (status) {
        case "done":
            return <CheckCircle size={16} className="upload-status-icon done" />;
        case "error":
            return <AlertCircle size={16} className="upload-status-icon error" />;
        case "uploading":
            return <Upload size={16} className="upload-status-icon uploading" />;
        case "queued":
            return <Clock size={16} className="upload-status-icon queued" />;
        case "paused":
            return <WifiOff size={16} className="upload-status-icon paused" />;
        default:
            return <Clock size={16} className="upload-status-icon waiting" />;
    }
}

export default function UploadProgress({ uploads, onCancel, onRetry }) {
    const entries = Object.entries(uploads);
    const [isOnline, setIsOnline] = useState(navigator.onLine);
    const [isMinimized, setIsMinimized] = useState(false);

    // Track online/offline status
    useEffect(() => {
        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);
        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);
        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    if (entries.length === 0) return null;

    const totalFiles = entries.length;
    const doneCount = entries.filter(([, u]) => u.status === "done").length;
    const errorCount = entries.filter(([, u]) => u.status === "error").length;
    const activeUpload = entries.find(([, u]) => u.status === "uploading");

    const totalBytes = entries.reduce((sum, [, u]) => sum + (u.total || 0), 0);
    const loadedBytes = entries.reduce((sum, [, u]) => sum + (u.loaded || 0), 0);
    const overallPercent = totalBytes > 0 ? Math.round((loadedBytes / totalBytes) * 100) : 0;

    return (
        <div className={`upload-progress-container ${isMinimized ? 'minimized' : ''}`}>
            <button
                type="button"
                className="upload-progress-header"
                onClick={() => setIsMinimized(!isMinimized)}
            >
                <div className="upload-progress-title">
                    <Upload size={18} />
                    <span>
                        {doneCount === totalFiles
                            ? `${totalFiles} file${totalFiles > 1 ? "s" : ""} uploaded`
                            : `Uploading ${doneCount + 1} of ${totalFiles}`}
                    </span>
                    {!isOnline && (
                        <span className="upload-offline-badge">
                            <WifiOff size={12} />
                            Offline
                        </span>
                    )}
                </div>
                <div className="upload-progress-actions">
                    {activeUpload && (
                        <span className="upload-speed-badge">
                            <Zap size={12} />
                            {formatSpeed(activeUpload[1].speed)}
                        </span>
                    )}
                    {errorCount > 0 && onRetry && (
                        <button
                            className="upload-retry-btn"
                            onClick={(e) => { e.stopPropagation(); onRetry(); }}
                            title="Retry failed uploads"
                        >
                            <RefreshCw size={14} />
                        </button>
                    )}
                    {onCancel && doneCount < totalFiles && (
                        <button
                            className="upload-cancel-btn"
                            onClick={(e) => { e.stopPropagation(); onCancel(); }}
                            title="Cancel upload"
                        >
                            <X size={16} />
                        </button>
                    )}
                </div>
            </button>

            <div className="upload-bar overall">
                <div
                    className={`upload-bar-fill ${!isOnline ? 'paused' : ''}`}
                    style={{ width: `${overallPercent}%` }}
                />
            </div>

            {!isMinimized && (
                <div className="upload-file-list">
                    {entries.map(([id, upload]) => (
                        <div key={id} className={`upload-item ${upload.status}`}>
                            <StatusIcon status={upload.status} />
                            <div className="upload-item-info">
                                <span className="upload-item-name" title={upload.name}>
                                    {upload.name}
                                </span>
                                <span className="upload-item-meta">
                                    {upload.status === "uploading" && (
                                        <>
                                            {formatBytes(upload.loaded)} / {formatBytes(upload.total)}
                                            {upload.eta > 0 && <> {" - "}{formatEta(upload.eta)}</>}
                                        </>
                                    )}
                                    {upload.status === "done" && formatBytes(upload.total)}
                                    {upload.status === "waiting" && formatBytes(upload.total)}
                                    {upload.status === "queued" && `${formatBytes(upload.total)} — Queued`}
                                    {upload.status === "paused" && `${formatBytes(upload.loaded || 0)} / ${formatBytes(upload.total)} — Paused`}
                                    {upload.status === "error" && "Failed — will retry"}
                                </span>
                            </div>
                            <span className="upload-item-percent">
                                {upload.status === "done" ? "✓" :
                                 upload.status === "error" ? "!" :
                                 upload.status === "paused" ? "⏸" :
                                 `${upload.percent}%`}
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {/* Network status indicator */}
            {!isOnline && (
                <div className="upload-network-banner">
                    <WifiOff size={14} />
                    <span>You're offline. Uploads will resume when reconnected.</span>
                </div>
            )}

            {isOnline && errorCount > 0 && (
                <div className="upload-network-banner retry">
                    <Wifi size={14} />
                    <span>{errorCount} upload{errorCount > 1 ? 's' : ''} failed. </span>
                    {onRetry && (
                        <button className="upload-retry-link" onClick={onRetry}>Retry now</button>
                    )}
                </div>
            )}
        </div>
    );
}
