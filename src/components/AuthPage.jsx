import React, { useState, useEffect, useRef } from 'react';
import { Eye, EyeOff, AlertCircle, User, Lock } from 'lucide-react';
import api from '../api';

export default function AuthPage({ onLogin }) {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const starsRef = useRef(null);
    const windsRef = useRef(null);

    // Generate twinkling stars dynamically
    useEffect(() => {
        const container = starsRef.current;
        if (!container) return;
        container.innerHTML = '';
        const count = window.innerWidth < 768 ? 80 : 120;
        for (let i = 0; i < count; i++) {
            const star = document.createElement('div');
            star.className = 'sky-star';
            star.style.cssText = `
                left: ${Math.random() * 100}%;
                top: ${Math.random() * 100}%;
                --star-dur: ${2 + Math.random() * 4}s;
                --star-delay: ${Math.random() * 6}s;
                --star-max-op: ${0.15 + Math.random() * 0.5};
                width: ${1 + Math.random() * 2}px;
                height: ${1 + Math.random() * 2}px;
            `;
            container.appendChild(star);
        }
    }, []);

    // Generate wind streaks dynamically
    useEffect(() => {
        const container = windsRef.current;
        if (!container) return;
        container.innerHTML = '';
        const positions = [8, 18, 28, 42, 55, 63, 72, 82, 91];
        positions.forEach((top) => {
            const wind = document.createElement('div');
            wind.className = 'sky-login__wind';
            const dur = (1.2 + Math.random() * 2).toFixed(1);
            const del = (Math.random() * 5).toFixed(1);
            const wid = 20 + Math.random() * 20;
            wind.style.cssText = `
                top: ${top}%;
                --wind-duration: ${dur}s;
                --wind-delay: ${del}s;
                width: ${wid}%;
            `;
            container.appendChild(wind);
        });
    }, []);

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
            {/* Dynamic stars */}
            <div className="sky-stars" ref={starsRef} />

            {/* Dynamic wind streaks */}
            <div className="sky-winds" ref={windsRef} />

            {/* Background clouds */}
            <div className="sky-login__bg">
                <div className="sky-login__cloud-bg sky-login__cloud-bg--1" />
                <div className="sky-login__cloud-bg sky-login__cloud-bg--2" />
            </div>

            {/* Header */}
            <header className="sky-login__header">
                <h1 className="sky-login__title">Home Cloud</h1>
                <p className="sky-login__subtitle sky-login__subtitle--desktop">Your files, floating gracefully.</p>
            </header>

            {/* Error message */}
            {error && (
                <div className="sky-login__error">
                    <AlertCircle size={16} />
                    <span>{error}</span>
                </div>
            )}

            {/* ======= DESKTOP LAYOUT: 3 clouds side-by-side ======= */}
            <form onSubmit={handleSubmit} className="sky-login__form sky-login__form--desktop">
                <div className="sky-login__field">
                    <div className="sky-login__cloud sky-login__cloud--1">
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--left" />
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--right" />
                    </div>
                    <div className="sky-login__string" />
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

                {!isLogin && (
                    <div className="sky-login__field">
                        <div className="sky-login__cloud sky-login__cloud--3">
                            <div className="sky-login__cloud-bump sky-login__cloud-bump--left-sm" />
                            <div className="sky-login__cloud-bump sky-login__cloud-bump--right-xs" />
                        </div>
                        <div className="sky-login__string" />
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

                <div className="sky-login__field">
                    <div className="sky-login__cloud sky-login__cloud--2">
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--left-lg" />
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--right-md" />
                    </div>
                    <div className="sky-login__string" />
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

                <div className="sky-login__field">
                    <div className="sky-login__cloud sky-login__cloud--3">
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--left-sm" />
                        <div className="sky-login__cloud-bump sky-login__cloud-bump--right-xs" />
                    </div>
                    <div className="sky-login__string" />
                    <button type="submit" className="sky-login__submit" disabled={loading}>
                        {loading ? 'Please wait...' : (isLogin ? 'Login' : 'Create Account')}
                    </button>
                </div>
            </form>

            {/* ======= MOBILE LAYOUT: single cloud with vertical rig ======= */}
            <form onSubmit={handleSubmit} className="sky-login__form sky-login__form--mobile">
                <div className="sky-rig">
                    {/* Single cloud */}
                    <div className="sky-rig__cloud">
                        <div className="sky-rig__cloud-bump sky-rig__cloud-bump--1" />
                        <div className="sky-rig__cloud-bump sky-rig__cloud-bump--2" />
                        <div className="sky-rig__cloud-bump sky-rig__cloud-bump--3" />
                        <div className="sky-rig__cloud-body" />
                    </div>

                    {/* Thread cloud → email */}
                    <div className="sky-rig__thread sky-rig__thread--long" />

                    {/* Email field */}
                    <div className="sky-rig__card">
                        <div className="sky-rig__card-inner">
                            <User size={18} className="sky-rig__icon" />
                            <input
                                type="email"
                                placeholder="Username or Email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    {/* Thread email → username (register only) */}
                    {!isLogin && (
                        <>
                            <div className="sky-rig__thread sky-rig__thread--short" />
                            <div className="sky-rig__card">
                                <div className="sky-rig__card-inner">
                                    <User size={18} className="sky-rig__icon" />
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
                        </>
                    )}

                    {/* Thread → password */}
                    <div className="sky-rig__thread sky-rig__thread--short" />

                    {/* Password field */}
                    <div className="sky-rig__card">
                        <div className="sky-rig__card-inner">
                            <Lock size={18} className="sky-rig__icon" />
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

                    {/* Login button */}
                    <div className="sky-rig__btn-wrap">
                        <button type="submit" className="sky-rig__btn" disabled={loading}>
                            <span>{loading ? 'Please wait...' : (isLogin ? 'Login' : 'Create Account')}</span>
                        </button>
                    </div>
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
