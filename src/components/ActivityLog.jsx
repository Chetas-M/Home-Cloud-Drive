import React from "react";
import {
    Upload,
    Download,
    FolderPlus,
    Edit3,
    Trash2,
    Star,
    RotateCcw,
} from "lucide-react";

const iconMap = {
    upload: Upload,
    download: Download,
    create_folder: FolderPlus,
    rename: Edit3,
    trash: Trash2,
    restore: RotateCcw,
    star: Star,
    login: Star,
    login_2fa: Star,
    logout: Star,
    empty_trash: Trash2,
};

const actionLabels = {
    upload: "Uploaded",
    download: "Downloaded",
    create_folder: "Created folder",
    rename: "Renamed",
    trash: "Moved to trash",
    restore: "Restored",
    star: "Starred",
    login: "Logged in",
    login_2fa: "Logged in (2FA)",
    logout: "Logged out",
    empty_trash: "Emptied trash",
};

function formatTime(timestamp) {
    const timestampMs = typeof timestamp === "string" || timestamp instanceof Date ? new Date(timestamp).getTime() : timestamp;
    const now = Date.now();
    const diff = now - timestampMs;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;

    return new Date(timestampMs).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
    });
}

export default function ActivityLog({ activities }) {
    if (!activities || activities.length === 0) {
        return (
            <div className="activity-log">
                <h3 className="activity-title">Recent Activity</h3>
                <p className="activity-empty">No recent activity</p>
            </div>
        );
    }

    return (
        <div className="activity-log">
            <h3 className="activity-title">Recent Activity</h3>
            <div className="activity-list">
                {activities.slice(0, 50).map((activity, index) => {
                    const Icon = iconMap[activity.action] || Upload;
                    return (
                        <div key={index} className="activity-item">
                            <div className="activity-icon">
                                <Icon size={14} />
                            </div>
                            <div className="activity-content">
                                <span className="activity-action">
                                    {actionLabels[activity.action] || activity.action}
                                </span>
                                {activity.file_name && <span className="activity-filename">{activity.file_name}</span>}
                                {(activity.details || activity.ip_address) && (
                                    <div className="activity-details" style={{fontSize: "0.8em", color: "#888", marginTop: "2px"}}>
                                        {[activity.details, activity.ip_address].filter(Boolean).join(" • ")}
                                    </div>
                                )}
                            </div>
                            <span className="activity-time">
                                {formatTime(activity.timestamp)}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
