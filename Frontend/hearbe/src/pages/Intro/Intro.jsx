import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import Spline from '@splinetool/react-spline';
import './Intro.css';

import introAudio1 from '../../assets/audio/intro/intro_guide_1.wav';
import introAudio2 from '../../assets/audio/intro/intro_guide_2.wav';
import introAudio3 from '../../assets/audio/intro/intro_guide_3.wav';

const STEPS = [
    {
        title: "목소리만으로 완성하는 쇼핑 경험",
        desc: "복잡한 화면 대신 당신의 목소리에 집중하는 스마트 쇼핑 파트너",
        audioSrc: introAudio1,
        duration: 4000,
    },
    {
        title: "스스로 선택하는 쇼핑",
        desc: "원하는 상품을 말해보세요. 당신의 목소리로 완벽한 쇼핑을 완성합니다.",
        audioSrc: introAudio2,
        duration: 4000,
    },
    {
        title: "HearBe와 함께 시작",
        desc: "모든 과정을 친절한 음성으로 안내하여 스스로 완성하는 쇼핑을 지원합니다.",
        audioSrc: introAudio3,
        duration: 4000,
    },
];

export default function Intro() {
    const [currentStep, setCurrentStep] = useState(0);
    const [isTransitioning, setIsTransitioning] = useState(false);
    const [hasStarted, setHasStarted] = useState(false);
    const [splineFailed, setSplineFailed] = useState(false);
    const splineLoadedRef = useRef(false);
    const navigate = useNavigate();

    const audioRef = useRef(null);
    const timerRef = useRef(null);
    const isMountedRef = useRef(true);

    useEffect(() => {
        const timeout = setTimeout(() => {
            if (!splineLoadedRef.current) {
                setSplineFailed(true);
            }
        }, 8000);
        return () => clearTimeout(timeout);
    }, []);

    const goToGuide = () => {
        if (isTransitioning) return;
        setIsTransitioning(true);
        setTimeout(() => navigate('/guide'), 850);
    };

    const handleStart = () => {
        setHasStarted(true);
    };

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.code === 'Space' || e.key === ' ' || e.code === 'Tab' || e.key === 'Tab') {
                e.preventDefault();

                if (!hasStarted) {
                    handleStart();
                } else {
                    if (currentStep < STEPS.length - 1) {
                        setCurrentStep(prev => prev + 1);
                    } else {
                        navigate('/guide');
                    }
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [hasStarted, currentStep, navigate]);

    useEffect(() => {
        if (!hasStarted || isTransitioning) return;
        if (timerRef.current) return;

        const handleNext = () => {
            if (!isMountedRef.current) return;
            if (currentStep < STEPS.length - 1) {
                setCurrentStep((prev) => prev + 1);
            } else {
                goToGuide();
            }
        };

        const audio = new Audio(STEPS[currentStep].audioSrc);
        audioRef.current = audio;

        const playPromise = audio.play();
        if (playPromise !== undefined) {
            playPromise.catch(() => {
                console.warn('Audio auto-play blocked.');
            });
        }

        timerRef.current = setTimeout(() => {
            if (isMountedRef.current) {
                handleNext();
            }
        }, STEPS[currentStep].duration);

        return () => {
            isMountedRef.current = false;

            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }

            if (timerRef.current) {
                clearTimeout(timerRef.current);
                timerRef.current = null;
            }

            setTimeout(() => {
                isMountedRef.current = true;
            }, 0);
        };
    }, [currentStep, hasStarted, isTransitioning]);

    if (!hasStarted) {
        return (
            <div className="intro-container cursor-pointer" onClick={handleStart} style={{ justifyContent: 'center' }}>
                <div className="text-section" style={{ marginTop: 0 }}>
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 1 }}
                    >
                        <h1 className="main-copy">HearBe 서비스 시작하기</h1>
                        <p className="sub-copy">스페이스바 또는 화면을 클릭하여 시작하세요</p>
                    </motion.div>
                </div>
                <div className="purple-aura" style={{ opacity: 0.2 }} />
            </div>
        );
    }

    return (
        <div className="intro-container">
            <button className="skip-btn cursor-pointer" onClick={() => navigate('/guide')}>
                skip
            </button>

            <AnimatePresence>
                {isTransitioning && (
                    <motion.div
                        className="transition-overlay"
                        initial={{ scale: 0 }}
                        animate={{ scale: 4 }}
                        transition={{ duration: 0.8 }}
                    />
                )}
            </AnimatePresence>

            <div className="text-section">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentStep}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.8 }}
                    >
                        <h1 className="main-copy">{STEPS[currentStep].title}</h1>
                        <p className="sub-copy">{STEPS[currentStep].desc}</p>
                    </motion.div>
                </AnimatePresence>
            </div>

            <div className="object-section">
                {splineFailed ? (
                    <div className="abstract-orb" />
                ) : (
                    <Spline
                        scene="https://prod.spline.design/IaDdv3c70ekbtAdf/scene.splinecode"
                        onLoad={() => {
                            splineLoadedRef.current = true;
                        }}
                        onError={() => setSplineFailed(true)}
                    />
                )}
            </div>

            <div className="action-section">
                <div className="dot-indicator">
                    {STEPS.map((_, i) => (
                        <div key={i} className={`dot ${i === currentStep ? 'active' : ''}`} />
                    ))}
                </div>
            </div>
        </div>
    );
}
