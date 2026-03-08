import React, { useState } from 'react';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import api from '../api';

export default function AuthPage({ onLogin }) {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (isLogin) {
                await api.login(email, password);
            } else {
                await api.register(email, username, password);
                await api.login(email, password);
            }
            const user = await api.getMe();
            onLogin(user);
        } catch (err) {
            setError(err.message || 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="sky-login">
            {/* Background decoration */}
            <div className="sky-login__bg">
                <div className="sky-login__cloud-bg sky-login__cloud-bg--1" />
                <div className="sky-login__cloud-bg sky-login__cloud-bg--2" />
                <div className="sky-login__wind" style={{ top: '15%', '--wind-duration': '2s', '--wind-delay': '0s' }} />
                <div className="sky-login__wind" style={{ top: '35%', '--wind-duration': '1.5s', '--wind-delay': '2s' }} />
                <div className="sky-login__wind" style={{ top: '55%', '--wind-duration': '2.5s', '--wind-delay': '1s' }} />
                <div className="sky-login__wind" style={{ top: '75%', '--wind-duration': '1.8s', '--wind-delay': '3s' }} />
                <div className="sky-login__wind" style={{ top: '90%', '--wind-duration': '3s', '--wind-delay': '0.5s' }} />
            </div>

            {/* Header */}
            <header className="sky-login__header">
                <h1 className="sky-login__title">CloudDrive</h1>
                <p className="sky-login__subtitle">Your files, floating gracefully.</p>
            </header>

            {/* Error message */}
            {error && (
                <div className="sky-login__error">
                    <AlertCircle size={16} />
                    <span>{error}</span>
                </div>
            )}

            {/* Login / Register form */}
            <form onSubmit={handleSubmit} className="sky-login__form">
                {/* Email field with cloud */}
                <div className="sky-login__field">
                    <div className="sky-login__cloud sky-login__cloud--1">
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--left" />
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--right" />
                    </div>
                    <div className="sky-login__string sky-login__string--1" />
                    <div className="sky-login__glass-input">
                        <input
                            type="email"
                            placeholder="Username or Email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                </div>

                {/* Username field (register only) */}
                {!isLogin && (
                    <div className="sky-login__field">
                        <div className="sky-login__cloud sky-login__cloud--2">
                            <div className="sky-login__cloud-bump sky-login__cloud-bump--left-sm" />
                            <div className="sky-login__cloud-bump sky-login__cloud-bump--right-sm" />
                        </div>
                        <div className="sky-login__string sky-login__string--2" />
                        <div className="sky-login__glass-input">
                            <input
                                type="text"
                                placeholder="Choose a username"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                minLength={3}
                                required
                            />
                        </div>
                    </div>
                )}

                {/* Password field with cloud */}
                <div className="sky-login__field">
                    <div className="sky-login__cloud sky-login__cloud--2">
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--left-lg" />
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--right-md" />
                    </div>
                    <div className="sky-login__string sky-login__string--2" />
                    <div className="sky-login__glass-input sky-login__glass-input--password">
                        <input
                            type={showPassword ? 'text' : 'password'}
                            placeholder="Password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            minLength={6}
                            required
                        />
                        <button
                            type="button"
                            className="sky-login__eye-toggle"
                            onClick={() => setShowPassword(!showPassword)}
                        >
                            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                        </button>
                    </div>
                </div>

                {/* Submit button with cloud */}
                <div className="sky-login__field">
                    <div className="sky-login__cloud sky-login__cloud--3">
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--left-sm" />
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--right-xs" />
                    </div>
                    <div className="sky-login__string sky-login__string--3" />
                    <button
                        type="submit"
                        className="sky-login__submit"
                        disabled={loading}
                    >
                        {loading ? 'Please wait...' : (isLogin ? 'Login' : 'Create Account')}
                    </button>
                </div>
            </form>

            {/* Footer links */}
            <footer className="sky-login__footer">
                <a href="#" onClick={(e) => e.preventDefault()}>Forgot Password?</a>
                <button
                    type="button"
                    onClick={() => { setIsLogin(!isLogin); setError(''); }}
                >
                    {isLogin ? 'Create Account' : 'Sign In'}
                </button>
                <a href="#" onClick={(e) => e.preventDefault()}>Help</a>
            </footer>
        </main>
    );
}
