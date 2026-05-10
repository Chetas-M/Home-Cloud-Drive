import React, { useState, useEffect } from 'react';
import { Share2, Copy, Check, X, Lock, Clock, Download, Link2, Trash2, Eye, BarChart3, Globe, Monitor, ChevronDown, ChevronUp } from 'lucide-react';
import api from '../api';

export default function ShareModal({ file, onClose }) {
    const [permission, setPermission] = useState('download');
    const [password, setPassword] = useState('');
    const [usePassword, setUsePassword] = useState(false);
    const [expiresHours, setExpiresHours] = useState('');
    const [maxDownloads, setMaxDownloads] = useState('');
    const [existingLinks, setExistingLinks] = useState([]);
    const [newLink, setNewLink] = useState(null);
    const [copied, setCopied] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [analyticsByLink, setAnalyticsByLink] = useState({});
    const [analyticsLoadingLink, setAnalyticsLoadingLink] = useState(null);
    const [expandedLink, setExpandedLink] = useState(null);

    useEffect(() => {
        loadLinks();
    }, []);

    const loadLinks = async () => {
        try {
            const links = await api.getMyShareLinks();
            setExistingLinks(links.filter(l => l.file_id === file.id && l.is_active));
        } catch (err) {
            console.error('Failed to load share links:', err);
        }
    };

    const handleCreate = async () => {
        const trimmedPassword = password.trim();

        if (usePassword && !trimmedPassword) {
            setError('Enter a password to protect this share link.');
            return;
        }

        try {
            setLoading(true);
            setError('');
            const data = {
                file_id: file.id,
                permission,
            };
            if (usePassword) data.password = trimmedPassword;
            if (expiresHours) data.expires_in_hours = parseInt(expiresHours);
            if (maxDownloads) data.max_downloads = parseInt(maxDownloads);

            const link = await api.createShareLink(data);
            setNewLink(link);
            setPassword('');
            setUsePassword(false);
            loadLinks();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleCopy = () => {
        const url = `${window.location.origin}/shared/${newLink.token}`;
        navigator.clipboard.writeText(url);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleUsePasswordChange = (e) => {
        setUsePassword(e.target.checked);
        if (!e.target.checked) setPassword('');
    };

    const handleRevoke = async (linkId) => {
        try {
            await api.revokeShareLink(linkId);
            loadLinks();
            if (expandedLink === linkId) {
                setExpandedLink(null);
            }
            setAnalyticsByLink(prev => {
                const next = { ...prev };
                delete next[linkId];
                return next;
            });
        } catch (err) {
            setError(err.message);
        }
    };

    const loadAnalytics = async (linkId) => {
        if (expandedLink === linkId) {
            setExpandedLink(null);
            return;
        }
        setExpandedLink(linkId);
        if (analyticsByLink[linkId]) return;
        setAnalyticsLoadingLink(linkId);
        try {
            const data = await api.getShareAnalytics(linkId);
            setAnalyticsByLink(prev => ({ ...prev, [linkId]: data }));
        } catch (err) {
            console.error('Failed to load analytics:', err);
        } finally {
            setAnalyticsLoadingLink(current => (current === linkId ? null : current));
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return 'Never';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now - d;
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
    };

    const parseUA = (ua) => {
        if (!ua) return 'Unknown device';
        if (ua.includes('Mobile')) return 'Mobile';
        if (ua.includes('Chrome')) return 'Chrome';
        if (ua.includes('Firefox')) return 'Firefox';
        if (ua.includes('Safari')) return 'Safari';
        if (ua.includes('Edge')) return 'Edge';
        return 'Browser';
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content share-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3><Share2 size={18} /> Share "{file.name}"</h3>
                    <button className="modal-close" onClick={onClose}><X size={18} /></button>
                </div>

                {error && <div className="share-error">{error}</div>}

                {newLink ? (
                    <div className="share-link-created">
                        <div className="share-success-icon"><Check size={32} /></div>
                        <p className="share-success-text">Share link created!</p>
                        <div className="share-link-url">
                            <input
                                type="text"
                                readOnly
                                value={`${window.location.origin}/shared/${newLink.token}`}
                            />
                            <button className="share-copy-btn" onClick={handleCopy}>
                                {copied ? <Check size={16} /> : <Copy size={16} />}
                                {copied ? 'Copied!' : 'Copy'}
                            </button>
                        </div>
                        <div className="share-link-details">
                            {newLink.has_password && <span className="share-badge"><Lock size={12} /> Password protected</span>}
                            {newLink.expires_at && <span className="share-badge"><Clock size={12} /> Expires {new Date(newLink.expires_at).toLocaleDateString()}</span>}
                            {newLink.max_downloads && <span className="share-badge"><Download size={12} /> Max {newLink.max_downloads} downloads</span>}
                        </div>
                        <button className="share-new-btn" onClick={() => setNewLink(null)}>Create another link</button>
                    </div>
                ) : (
                    <div className="share-form">
                        {/* Permission */}
                        <div className="share-field">
                            <label>Permission</label>
                            <div className="share-permission-toggle">
                                <button
                                    className={`share-perm-btn ${permission === 'view' ? 'active' : ''}`}
                                    onClick={() => setPermission('view')}
                                >
                                    <Eye size={14} /> View only
                                </button>
                                <button
                                    className={`share-perm-btn ${permission === 'download' ? 'active' : ''}`}
                                    onClick={() => setPermission('download')}
                                >
                                    <Download size={14} /> Download
                                </button>
                            </div>
                        </div>

                        {/* Password */}
                        <div className="share-field">
                            <label className="share-checkbox-label">
                                <input type="checkbox" checked={usePassword} onChange={handleUsePasswordChange} />
                                <Lock size={14} /> Password protect
                            </label>
                            {usePassword && (
                                <input
                                    type="password"
                                    placeholder="Enter password..."
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    className="share-input"
                                />
                            )}
                        </div>

                        {/* Expiry */}
                        <div className="share-field">
                            <label><Clock size={14} /> Expires after</label>
                            <select value={expiresHours} onChange={e => setExpiresHours(e.target.value)} className="share-select">
                                <option value="">Never</option>
                                <option value="1">1 hour</option>
                                <option value="24">1 day</option>
                                <option value="168">1 week</option>
                                <option value="720">30 days</option>
                            </select>
                        </div>

                        {/* Max downloads */}
                        <div className="share-field">
                            <label><Download size={14} /> Max downloads</label>
                            <select value={maxDownloads} onChange={e => setMaxDownloads(e.target.value)} className="share-select">
                                <option value="">Unlimited</option>
                                <option value="1">1</option>
                                <option value="5">5</option>
                                <option value="10">10</option>
                                <option value="50">50</option>
                            </select>
                        </div>

                        <button
                            className="share-create-btn"
                            onClick={handleCreate}
                            disabled={loading || (usePassword && !password.trim())}
                        >
                            <Link2 size={16} />
                            {loading ? 'Creating...' : 'Create share link'}
                        </button>
                    </div>
                )}

                {/* Existing links with analytics */}
                {existingLinks.length > 0 && (
                    <div className="share-existing">
                        <h4>Active links ({existingLinks.length})</h4>
                        <div className="share-links-list">
                            {existingLinks.map(link => {
                                const analytics = analyticsByLink[link.id];
                                return (
                                <div key={link.id} className="share-link-item-wrapper">
                                    <div className="share-link-item">
                                        <div className="share-link-info">
                                            <span className="share-link-perm">{link.permission === 'download' ? '⬇️' : '👁️'} {link.permission}</span>
                                            <span className="share-link-meta">{link.download_count} downloads</span>
                                            {link.last_accessed_at && (
                                                <span className="share-link-meta share-link-last-access">
                                                    <Clock size={10} /> {formatDate(link.last_accessed_at)}
                                                </span>
                                            )}
                                            {link.has_password && <Lock size={12} />}
                                        </div>
                                        <div className="share-link-actions">
                                            <button
                                                className="share-analytics-btn"
                                                onClick={() => loadAnalytics(link.id)}
                                                title="View analytics"
                                            >
                                                <BarChart3 size={14} />
                                                {expandedLink === link.id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                            </button>
                                            <button className="share-revoke-btn" onClick={() => handleRevoke(link.id)}>
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Analytics Panel */}
                                    {expandedLink === link.id && (
                                        <div className="share-analytics-panel">
                                            {analyticsLoadingLink === link.id ? (
                                                 <div className="share-analytics-loading">Loading analytics...</div>
                                            ) : analytics ? (
                                                <>
                                                     <div className="share-analytics-stats">
                                                         <div className="analytics-stat">
                                                             <Download size={14} />
                                                            <span className="analytics-stat-value">{analytics.total_downloads}</span>
                                                            <span className="analytics-stat-label">Downloads</span>
                                                        </div>
                                                        <div className="analytics-stat">
                                                            <Eye size={14} />
                                                            <span className="analytics-stat-value">{analytics.total_views}</span>
                                                            <span className="analytics-stat-label">Views</span>
                                                        </div>
                                                        <div className="analytics-stat">
                                                            <Clock size={14} />
                                                            <span className="analytics-stat-value">{formatDate(analytics.last_accessed_at)}</span>
                                                            <span className="analytics-stat-label">Last Access</span>
                                                        </div>
                                                    </div>

                                                     {analytics.access_history.length > 0 && (
                                                         <div className="share-access-history">
                                                             <h5>Access History</h5>
                                                            <div className="access-history-list">
                                                                {analytics.access_history.slice(0, 10).map(entry => (
                                                                    <div key={entry.id} className="access-history-item">
                                                                        <div className="access-history-icon">
                                                                            {entry.action === 'download' ? <Download size={12} /> : <Eye size={12} />}
                                                                        </div>
                                                                        <div className="access-history-details">
                                                                            <span className="access-history-action">{entry.action}</span>
                                                                            <span className="access-history-device">
                                                                                <Monitor size={10} /> {parseUA(entry.user_agent)}
                                                                            </span>
                                                                        </div>
                                                                        <div className="access-history-meta">
                                                                            <span className="access-history-ip">
                                                                                <Globe size={10} /> {entry.ip_address || 'Unknown'}
                                                                            </span>
                                                                            <span className="access-history-time">
                                                                                {formatDate(entry.accessed_at)}
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                         </div>
                                                     )}
                                                </>
                                            ) : (
                                                <div className="share-analytics-loading">No analytics available</div>
                                            )}
                                        </div>
                                    )}
                                </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
