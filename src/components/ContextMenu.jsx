import React, { useEffect, useState } from "react";
import {
    Download,
    Star,
    StarOff,
    Edit3,
    Trash2,
    FolderInput,
    Eye,
    Copy,
    Info,
    Share2,
    History,
    X,
} from "lucide-react";

export default function ContextMenu({
    x,
    y,
    file,
    isStarred,
    onClose,
    onPreview,
    onDownload,
    onStar,
    onRename,
    onMove,
    onCopy,
    onTrash,
    onDetails,
    onShare,
    onVersions,
}) {
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        setIsMobile(window.innerWidth <= 768);
    }, []);

    // Prevent body scroll on mobile when context menu is open
    useEffect(() => {
        if (isMobile) {
            const previousOverflow = document.body.style.overflow;
            document.body.style.overflow = 'hidden';
            return () => {
                if (previousOverflow) {
                    document.body.style.overflow = previousOverflow;
                } else {
                    document.body.style.removeProperty('overflow');
                }
            };
        }
    }, [isMobile]);

    const menuItems = [
        { icon: Eye, label: "Preview", action: onPreview, show: file.type !== "folder" },
        { icon: Download, label: "Download", action: onDownload, show: file.type !== "folder" },
        { divider: true },
        { icon: isStarred ? StarOff : Star, label: isStarred ? "Unstar" : "Star", action: onStar, show: !file.is_shared || file.can_share_public },
        { icon: Edit3, label: "Rename", action: onRename, show: file.can_write },
        { icon: FolderInput, label: "Move to...", action: onMove, show: file.can_write },
        { icon: Copy, label: "Make a copy", action: onCopy, show: file.type !== "folder" && !file.is_shared },
        { icon: Share2, label: file.type === "folder" ? "Manage access" : "Share", action: onShare, show: file.type === "folder" ? file.can_manage && (!file.is_shared || file.is_shared_root) : file.can_share_public },
        { divider: true },
        { icon: History, label: "Version history", action: onVersions, show: file.type !== "folder" },
        { icon: Info, label: "Details", action: onDetails },
        { icon: Trash2, label: "Move to Trash", action: onTrash, danger: true, show: file.can_manage },
    ];

    const handleClick = (action) => {
        action?.();
        onClose();
    };

    // Adjust position to keep menu in viewport (desktop only)
    const adjustedX = Math.min(x, window.innerWidth - 220);
    const adjustedY = Math.min(y, window.innerHeight - 350);

    if (isMobile) {
        return (
            <>
                <div className="context-menu-overlay mobile-sheet-overlay" onClick={onClose} />
                <div className="context-menu-bottom-sheet">
                    <div className="bottom-sheet-header">
                        <div className="bottom-sheet-handle" />
                        <div className="bottom-sheet-title">
                            <span className="bottom-sheet-filename">{file.name}</span>
                            <button className="bottom-sheet-close" onClick={onClose}>
                                <X size={20} />
                            </button>
                        </div>
                    </div>
                    <div className="bottom-sheet-items">
                        {menuItems.map((item, index) => {
                            if (item.divider) {
                                return <div key={index} className="context-menu-divider" />;
                            }
                            if (item.show === false) return null;
                            const Icon = item.icon;
                            return (
                                <button
                                    key={index}
                                    className={`bottom-sheet-item ${item.danger ? "danger" : ""}`}
                                    onClick={() => handleClick(item.action)}
                                >
                                    <Icon size={20} />
                                    <span>{item.label}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </>
        );
    }

    return (
        <>
            <div className="context-menu-overlay" onClick={onClose} />
            <div
                className="context-menu"
                style={{ left: adjustedX, top: adjustedY }}
            >
                {menuItems.map((item, index) => {
                    if (item.divider) {
                        return <div key={index} className="context-menu-divider" />;
                    }
                    if (item.show === false) return null;
                    const Icon = item.icon;
                    return (
                        <button
                            key={index}
                            className={`context-menu-item ${item.danger ? "danger" : ""}`}
                            onClick={() => handleClick(item.action)}
                        >
                            <Icon size={16} />
                            <span>{item.label}</span>
                        </button>
                    );
                })}
            </div>
        </>
    );
}
