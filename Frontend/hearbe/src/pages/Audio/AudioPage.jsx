import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Spline from '@splinetool/react-spline';
import './AudioPage.css';

const PARTICLE_COUNT = 20;
const COMMAND_NAV_DELAY_MS = 420;

function hasWebGLSupport() {
    try {
        const canvas = document.createElement('canvas');
        return Boolean(
            canvas.getContext('webgl2') ||
            canvas.getContext('webgl') ||
            canvas.getContext('experimental-webgl')
        );
    } catch {
        return false;
    }
}

function getThemeByPath(pathname) {
    const normalizedPath = pathname.toLowerCase();

    if (normalizedPath.includes('/login')) {
        return { primary: '#c4b5fd', secondary: '#a78bfa' }; // light purple
    }
    if (normalizedPath.includes('/signup')) {
        return { primary: '#34d399', secondary: '#27EDE9' }; // green
    }
    if (normalizedPath.includes('/findid')) {
        return { primary: '#6ee7b7', secondary: '#27EDE9' }; // mint
    }
    if (normalizedPath.includes('/changepassword') || normalizedPath.includes('/findpassword')) {
        return { primary: '#fde047', secondary: '#eab308' }; // yellow
    }
    if (normalizedPath.includes('/selectmall') || normalizedPath.endsWith('/mall')) {
        return { primary: '#f87171', secondary: '#ef4444' }; // red
    }
    if (normalizedPath.includes('/cardmanagement') || normalizedPath.includes('/card-management')) {
        return { primary: '#5eead4', secondary: '#06b6d4' }; // blue-green
    }
    if (normalizedPath.includes('/wishlist')) {
        return { primary: '#f9a8d4', secondary: '#ec4899' }; // pink
    }
    if (normalizedPath.includes('/memberinfo') || normalizedPath.includes('/member-info')) {
        return { primary: '#ffffff', secondary: '#f1f5f9' }; // white
    }
    if (normalizedPath.includes('/cart')) {
        return { primary: '#fb923c', secondary: '#f97316' }; // orange
    }
    if (normalizedPath.includes('/orderhistory') || normalizedPath.includes('/order-history')) {
        return { primary: '#c4b5fd', secondary: '#a78bfa' }; // muted lavender
    }

    return { primary: '#7dd3fc', secondary: '#38bdf8' };
}

function resolveVoiceTarget(transcript) {
    const raw = transcript.toLowerCase();
    const compact = raw.replace(/\s+/g, '');
    const has = (...keywords) => keywords.some((keyword) => compact.includes(keyword));

    if (has('쿠팡') || /coupang/i.test(raw)) return 'https://www.coupang.com';
    if (has('로그인', '로그인해줘', '로그인해주세요') || /log\s?in/i.test(raw)) return '/A/login';
    if (has('회원가입', '가입해줘', '가입해주세요') || /sign\s?up/i.test(raw) || /사인업/i.test(raw)) return '/A/signup';
    if (has('아이디찾기', '아이디찾아줘', '아이디찾아', 'id찾기') || /find\s?id/i.test(raw)) return '/A/findId';
    if (has('비밀번호변경', '비번변경', '비밀번호바꿔', '비번바꿔', '패스워드변경') || /change\s?password/i.test(raw)) return '/A/changePassword';
    if (has('비밀번호찾기', '비번찾기', '패스워드찾기', '비밀번호찾아줘') || /find\s?password/i.test(raw)) return '/A/findPassword';
    if (has('쇼핑몰', '몰선택', '몰고르기') || /select\s?mall/i.test(raw)) return '/A/selectMall';
    if (has('카드관리', '카드관리페이지', '카드등록', '카드정보') || /card\s?management/i.test(raw)) return '/A/cardManagement';
    if (has('찜', '위시리스트') || /wishlist/i.test(raw)) return '/A/wishlist';
    if (has('회원정보', '회원ㄱ정보', '멤버정보', '내정보', '마이페이지') || /member\s?info/i.test(raw)) return '/A/memberInfo';
    if (has('장바구니', '카트') || /cart/i.test(raw)) return '/A/cart';
    if (has('주문내역', '주문기록', '주문조회') || /order\s?history/i.test(raw)) return '/A/orderHistory';
    if (has('메인') || /main/i.test(raw)) return '/main';

    return null;
}

function shouldNavigateTarget(target) {
    return target.startsWith('/') || target.startsWith('http');
}

function WebGLFallback() {
    return (
        <div className="audio-fallback">
            <div>
                <h2>WebGL is unavailable</h2>
                <p>This environment cannot render Spline 3D.</p>
            </div>
        </div>
    );
}

export default function AudioPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const rootRef = useRef(null);
    const [previewPath, setPreviewPath] = useState('');
    const themePath = previewPath || location.pathname;
    const theme = useMemo(() => getThemeByPath(themePath), [themePath]);

    const [canRenderSpline, setCanRenderSpline] = useState(() => hasWebGLSupport());
    const [isListening, setIsListening] = useState(false);
    const [micLevel, setMicLevel] = useState(0);
    const [pulseBoost, setPulseBoost] = useState(0);
    const [phase, setPhase] = useState(0);
    const [speechDetected, setSpeechDetected] = useState(false);
    const [statusMessage, setStatusMessage] = useState('Hold Space and speak.');
    const [speechSupported] = useState(
        () => typeof window !== 'undefined' && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)
    );

    const recognitionRef = useRef(null);
    const streamRef = useRef(null);
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const sourceRef = useRef(null);
    const rafRef = useRef(null);
    const speechOffTimerRef = useRef(null);
    const navTimerRef = useRef(null);
    const holdingSpaceRef = useRef(false);

    const particles = useMemo(
        () =>
            Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
                id: i,
                angle: (360 / PARTICLE_COUNT) * i,
                radius: 90 + (i % 4) * 18,
                speed: 0.7 + (i % 5) * 0.14,
                size: 4 + (i % 3) * 2,
            })),
        []
    );

    const stopAudioPipeline = useCallback(() => {
        if (rafRef.current) {
            cancelAnimationFrame(rafRef.current);
            rafRef.current = null;
        }

        if (sourceRef.current) {
            sourceRef.current.disconnect();
            sourceRef.current = null;
        }

        if (analyserRef.current) {
            analyserRef.current.disconnect();
            analyserRef.current = null;
        }

        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }

        setMicLevel(0);
        setPulseBoost(0);
    }, []);

    const stopListening = useCallback((keepStatus = false) => {
        holdingSpaceRef.current = false;
        setIsListening(false);
        if (!keepStatus) {
            setStatusMessage('Hold Space and speak.');
        }

        if (recognitionRef.current) {
            try {
                recognitionRef.current.stop();
            } catch {
                // ignore stop errors from quick restart/stop cycles
            }
        }

        stopAudioPipeline();
    }, [stopAudioPipeline]);

    const startListening = useCallback(async () => {
        if (holdingSpaceRef.current) return;
        holdingSpaceRef.current = true;
        setIsListening(true);
        setStatusMessage('Listening...');

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });

            streamRef.current = stream;

            const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
            if (AudioContextCtor) {
                const audioContext = new AudioContextCtor();
                const analyser = audioContext.createAnalyser();
                analyser.fftSize = 1024;
                analyser.smoothingTimeConstant = 0.82;

                const source = audioContext.createMediaStreamSource(stream);
                source.connect(analyser);

                audioContextRef.current = audioContext;
                analyserRef.current = analyser;
                sourceRef.current = source;

                const timeData = new Uint8Array(analyser.fftSize);

                const animate = () => {
                    analyser.getByteTimeDomainData(timeData);

                    let sum = 0;
                    for (let i = 0; i < timeData.length; i += 1) {
                        const centered = (timeData[i] - 128) / 128;
                        sum += centered * centered;
                    }

                    const rms = Math.sqrt(sum / timeData.length);
                    const normalized = Math.min(1, rms * 5.5);

                    setMicLevel((prev) => prev * 0.75 + normalized * 0.25);
                    setPulseBoost((prev) => Math.max(prev * 0.91, normalized * 1.2));
                    setPhase((prev) => prev + 0.03);

                    rafRef.current = requestAnimationFrame(animate);
                };

                animate();
            }

            if (recognitionRef.current) {
                try {
                    recognitionRef.current.start();
                } catch {
                    // ignore duplicated start errors
                }
            } else if (!speechSupported) {
                setStatusMessage('Speech recognition unsupported. Volume-reactive FX only.');
            }
        } catch (error) {
            console.error('Microphone access failed:', error);
            setStatusMessage('Microphone permission is required.');
            stopListening();
        }
    }, [speechSupported, stopListening]);

    useEffect(() => {
        if (!speechSupported) return undefined;

        const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognitionCtor();
        recognition.lang = 'ko-KR';
        recognition.continuous = true;
        recognition.interimResults = true;

        recognition.onresult = (event) => {
            const result = event.results[event.results.length - 1];
            const transcript = result[0]?.transcript?.trim();

            if (!transcript) return;

            const target = resolveVoiceTarget(transcript);

            if (target) {
                setSpeechDetected(true);
                setPulseBoost((prev) => Math.min(1.2, prev + 0.38));
                setStatusMessage(`Command -> ${target}`);
                setPreviewPath(target);

                if (speechOffTimerRef.current) {
                    clearTimeout(speechOffTimerRef.current);
                }
                if (navTimerRef.current) {
                    clearTimeout(navTimerRef.current);
                }

                stopListening(true);
                if (shouldNavigateTarget(target)) {
                    navTimerRef.current = setTimeout(() => {
                        if (target.startsWith('http')) {
                            window.location.assign(target);
                        } else {
                            navigate(target);
                        }
                    }, COMMAND_NAV_DELAY_MS);
                }
                return;
            }

            setSpeechDetected(true);
            setPulseBoost((prev) => Math.min(1.2, prev + 0.28));
            setStatusMessage(`Recognized: ${transcript}`);

            if (speechOffTimerRef.current) {
                clearTimeout(speechOffTimerRef.current);
            }
            speechOffTimerRef.current = setTimeout(() => {
                setSpeechDetected(false);
                setStatusMessage('Listening...');
            }, 450);
        };

        recognition.onerror = (event) => {
            if (event.error === 'aborted' || event.error === 'no-speech') return;
            setStatusMessage('Speech recognition error: check mic permission/browser settings.');
        };

        recognition.onend = () => {
            if (holdingSpaceRef.current) {
                try {
                    recognition.start();
                } catch {
                    // ignore duplicated start errors
                }
            }
        };

        recognitionRef.current = recognition;

        return () => {
            if (speechOffTimerRef.current) {
                clearTimeout(speechOffTimerRef.current);
                speechOffTimerRef.current = null;
            }
            if (navTimerRef.current) {
                clearTimeout(navTimerRef.current);
                navTimerRef.current = null;
            }
            try {
                recognition.stop();
            } catch {
                // ignore stop errors
            }
            recognitionRef.current = null;
        };
    }, [navigate, speechSupported, stopListening]);

    useEffect(() => {
        const onKeyDown = (event) => {
            if (event.code !== 'Space') return;
            event.preventDefault();
            if (event.repeat) return;
            startListening();
        };

        const onKeyUp = (event) => {
            if (event.code !== 'Space') return;
            event.preventDefault();
            stopListening();
        };

        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup', onKeyUp);
        window.addEventListener('blur', stopListening);

        return () => {
            window.removeEventListener('keydown', onKeyDown);
            window.removeEventListener('keyup', onKeyUp);
            window.removeEventListener('blur', stopListening);
            stopListening();
        };
    }, [startListening, stopListening]);

    useEffect(() => {
        const node = rootRef.current;
        if (!node) return undefined;

        const preventWheel = (event) => {
            event.preventDefault();
        };

        node.addEventListener('wheel', preventWheel, { passive: false });
        return () => {
            node.removeEventListener('wheel', preventWheel);
        };
    }, []);

    if (!canRenderSpline) {
        return <WebGLFallback />;
    }

    const energy = Math.min(1, micLevel * 0.95 + pulseBoost * 0.35 + (speechDetected ? 0.22 : 0));
    const bloomSize = (170 + energy * 180) * 1.25;
    const haloSize = (280 + energy * 230) * 1.25;

    return (
        <div className="audio-page-root" ref={rootRef}>
            <div className="audio-spline-wrap">
                <Spline
                    scene="https://prod.spline.design/IaDdv3c70ekbtAdf/scene.splinecode"
                    onError={() => setCanRenderSpline(false)}
                />
            </div>

            <div className="audio-fx-overlay">
                <div
                    className={`audio-bloom ${isListening ? 'is-listening' : ''}`}
                    style={{
                        width: `${bloomSize}px`,
                        height: `${bloomSize}px`,
                        opacity: 0.18 + energy * 0.62,
                        background: `radial-gradient(circle, ${theme.primary} 0%, rgba(0,0,0,0) 68%)`,
                        filter: `blur(${34 + energy * 24}px)`,
                    }}
                />
                <div
                    className="audio-halo"
                    style={{
                        width: `${haloSize}px`,
                        height: `${haloSize}px`,
                        opacity: 0.14 + energy * 0.45,
                        borderColor: theme.secondary,
                        boxShadow: `0 0 ${90 + energy * 180}px ${theme.secondary}`,
                    }}
                />

                <div className="audio-particles">
                    {particles.map((particle) => {
                        const wave = Math.sin(phase * particle.speed + particle.angle * 0.03);
                        const radius = particle.radius + wave * 18 + energy * 56;
                        const opacity = Math.min(1, 0.26 + energy * 0.72);

                        return (
                            <span
                                key={particle.id}
                                className="audio-particle"
                                style={{
                                    width: `${particle.size}px`,
                                    height: `${particle.size}px`,
                                    opacity,
                                    backgroundColor: theme.secondary,
                                    transform: `translate(-50%, -50%) rotate(${particle.angle + phase * 25}deg) translateX(${radius}px)`,
                                }}
                            />
                        );
                    })}
                </div>
            </div>

            <div className="audio-hud">
                <span className={`audio-dot ${isListening ? 'active' : ''}`} />
                <span>{statusMessage}</span>
            </div>
        </div>
    );
}
