import React, { useState } from "react";
import { Trash2, RotateCcw, X, Check, CheckSquare, Square } from "lucide-react";

export default function TrashView({
    trashedFiles,
    onRestore,
    onDeletePermanently,
    onEmptyTrash,
    onBulkRestore,
    onBulkDelete,
}) {
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [isMultiSelect, setIsMultiSelect] = useState(false);

    const toggleSelect = (id) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const selectAll = () => {
        setSelectedIds(new Set(trashedFiles.map(f => f.id)));
    };

    const clearSelection = () => {
        setSelectedIds(new Set());
        setIsMultiSelect(false);
    };

    const handleBulkRestore = () => {
        if (onBulkRestore) {
            onBulkRestore(Array.from(selectedIds));
        } else {
            selectedIds.forEach(id => onRestore(id));
        }
        clearSelection();
    };

    const handleBulkDelete = () => {
        if (!confirm(`Permanently delete ${selectedIds.size} items? This cannot be undone.`)) return;
        if (onBulkDelete) {
            onBulkDelete(Array.from(selectedIds));
        } else {
            selectedIds.forEach(id => onDeletePermanently(id));
        }
        clearSelection();
    };

    if (trashedFiles.length === 0) {
        return (
            <div className="trash-empty">
                <Trash2 size={48} className="trash-empty-icon" />
                <h3>Trash is empty</h3>
                <p>Items you delete will appear here</p>
            </div>
        );
    }

    return (
        <div className="trash-view">
            <div className="trash-header">
                <div className="trash-header-left">
                    <span className="trash-count">
                        {trashedFiles.length} item{trashedFiles.length > 1 ? "s" : ""} in trash
                    </span>
                    <button
                        className={`trash-select-toggle ${isMultiSelect ? 'active' : ''}`}
                        onClick={() => {
                            setIsMultiSelect(!isMultiSelect);
                            if (isMultiSelect) clearSelection();
                        }}
                        title="Multi-select"
                    >
                        <CheckSquare size={16} />
                    </button>
                </div>

                <div className="trash-header-actions">
                    {isMultiSelect && selectedIds.size > 0 ? (
                        <>
                            <span className="trash-selected-count">{selectedIds.size} selected</span>
                            <button className="trash-bulk-btn select-all" onClick={selectAll}>
                                Select All
                            </button>
                            <button className="trash-bulk-btn restore" onClick={handleBulkRestore}>
                                <RotateCcw size={14} />
                                Restore
                            </button>
                            <button className="trash-bulk-btn delete" onClick={handleBulkDelete}>
                                <X size={14} />
                                Delete
                            </button>
                            <button className="trash-bulk-btn clear" onClick={clearSelection}>
                                <X size={14} />
                            </button>
                        </>
                    ) : (
                        <button className="empty-trash-btn" onClick={onEmptyTrash}>
                            <Trash2 size={16} />
                            Empty Trash
                        </button>
                    )}
                </div>
            </div>

            <div className="trash-list">
                {trashedFiles.map((file) => (
                    <div
                        key={file.id}
                        className={`trash-item ${selectedIds.has(file.id) ? 'selected' : ''}`}
                        onClick={() => isMultiSelect && toggleSelect(file.id)}
                    >
                        {isMultiSelect && (
                            <button
                                className={`trash-checkbox ${selectedIds.has(file.id) ? 'checked' : ''}`}
                                onClick={(e) => { e.stopPropagation(); toggleSelect(file.id); }}
                            >
                                {selectedIds.has(file.id) ? <Check size={14} /> : <Square size={14} />}
                            </button>
                        )}
                        <span className="trash-item-name">{file.name}</span>
                        {file.trashed_at && (
                            <span className="trash-item-date">
                                {new Date(file.trashed_at).toLocaleDateString()}
                            </span>
                        )}
                        <div className="trash-item-actions">
                            <button
                                className="trash-action restore"
                                onClick={(e) => { e.stopPropagation(); onRestore(file.id); }}
                                title="Restore"
                            >
                                <RotateCcw size={16} />
                            </button>
                            <button
                                className="trash-action delete"
                                onClick={(e) => { e.stopPropagation(); onDeletePermanently(file.id); }}
                                title="Delete forever"
                            >
                                <X size={16} />
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
