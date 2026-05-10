import React from "react";
import {
    Trash2,
    FolderInput,
    Copy,
    Download,
    X,
    Share2,
    RotateCcw,
    CheckSquare,
    Loader,
} from "lucide-react";

export default function BulkActionBar({
    selectedCount,
    currentView,
    onBulkTrash,
    onBulkRestore,
    onBulkCopy,
    onBulkMove,
    onBulkDownload,
    onBulkShare,
    onClearSelection,
    loading,
}) {
    if (selectedCount === 0) return null;

    const isTrashView = currentView === "trash";

    return (
        <div className="bulk-action-bar">
            <div className="bulk-action-bar-inner">
                <div className="bulk-info">
                    <CheckSquare size={16} />
                    <span className="bulk-count">{selectedCount} selected</span>
                </div>

                <div className="bulk-actions">
                    {isTrashView ? (
                        <>
                            <button
                                className="bulk-btn restore"
                                onClick={onBulkRestore}
                                disabled={loading}
                                title="Restore selected"
                            >
                                <RotateCcw size={16} />
                                <span>Restore</span>
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                className="bulk-btn"
                                onClick={onBulkMove}
                                disabled={loading}
                                title="Move selected"
                            >
                                <FolderInput size={16} />
                                <span>Move</span>
                            </button>
                            <button
                                className="bulk-btn"
                                onClick={onBulkCopy}
                                disabled={loading}
                                title="Copy selected"
                            >
                                <Copy size={16} />
                                <span>Copy</span>
                            </button>
                            <button
                                className="bulk-btn"
                                onClick={onBulkDownload}
                                disabled={loading}
                                title="Download selected"
                            >
                                <Download size={16} />
                                <span>Download</span>
                            </button>
                            <button
                                className="bulk-btn"
                                onClick={onBulkShare}
                                disabled={loading}
                                title="Share selected"
                            >
                                <Share2 size={16} />
                                <span>Share</span>
                            </button>
                            <button
                                className="bulk-btn danger"
                                onClick={onBulkTrash}
                                disabled={loading}
                                title="Trash selected"
                            >
                                <Trash2 size={16} />
                                <span>Trash</span>
                            </button>
                        </>
                    )}
                </div>

                <button
                    className="bulk-close-btn"
                    onClick={onClearSelection}
                    title="Clear selection"
                >
                    {loading ? <Loader size={16} className="spin" /> : <X size={16} />}
                </button>
            </div>
        </div>
    );
}
