import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ChevronRight,
    ChevronDown,
    Mic,
    Eye,
    Command,
    ArrowRight,
    Volume2,
    Layout,
    Share2
} from 'lucide-react';
import logoC from '../../assets/logoC.png';
import guideAudio1 from '../../assets/audio/guide/brand_guide_1.wav';
import guideAudio2 from '../../assets/audio/guide/brand_guide_2.wav';
import guideAudio3 from '../../assets/audio/guide/brand_guide_3.wav';

const WaveBackground = () => (
    <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <svg className="absolute left-0 w-[200%] h-full opacity-[0.03] animate-wave" viewBox="0 0 1000 1000" preserveAspectRatio="none">
            <path d="M0,500 C150,400 350,600 500,500 C650,400 850,600 1000,500 L1000,1000 L0,1000 Z" fill="url(#wave-gradient)" />
            <defs>
                <linearGradient id="wave-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#7C3AED" />
                    <stop offset="100%" stopColor="#3B82F6" />
                </linearGradient>
            </defs>
        </svg>
    </div>
);

const BrandLanding = () => {
    const navigate = useNavigate();
    const [currentStep, setCurrentStep] = useState(0);
    const timerRef = useRef(null);
    const audioRef = useRef(null);
    const isMountedRef = useRef(true);

    const goToMain = () => {
        navigate('/main');
    };

    const GUIDE_STEPS = [
        {
            id: 'speciality',
            audioSrc: guideAudio1,
            duration: 8000,
            content: (
                <section className="min-w-screen h-full flex flex-col justify-center items-center relative px-8 shrink-0">
                    <div className="max-w-7xl w-full">
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6 }}
                            className="text-center mb-12"
                        >
                            <h2 className="text-5xl font-black mb-4 text-gray-900 tracking-tight">HearBe의 특별함</h2>
                            <p className="text-xl text-gray-500 font-medium">평등한 쇼핑 가치를 전달하는 핵심 기술</p>
                        </motion.div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            {[
                                {
                                    icon: <Mic size={32} />,
                                    color: "bg-purple-100 text-purple-600",
                                    title: "보이스 컨트롤",
                                    desc: "검색부터 결제까지,\n목소리 하나로 편리하게."
                                },
                                {
                                    icon: <Eye size={32} />,
                                    color: "bg-indigo-100 text-indigo-600",
                                    title: "초고대비 모드",
                                    desc: "저시력 사용자를 위한\n최적의 시각 경험 제공."
                                },
                                {
                                    icon: <Command size={32} />,
                                    color: "bg-pink-100 text-pink-600",
                                    title: "음성 명령 브릿지",
                                    desc: "사용자의 의도를 파악하는\n지능형 인터페이스."
                                }
                            ].map((item, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.1 + i * 0.1, duration: 0.5 }}
                                    className="bg-white rounded-[2.5rem] p-10 shadow-lg border border-gray-100 hover:-translate-y-2 transition-all duration-300"
                                >
                                    <div className={`w-16 h-16 rounded-2xl ${item.color} flex items-center justify-center mb-6`}>
                                        {item.icon}
                                    </div>
                                    <h3 className="text-2xl font-bold mb-4 text-gray-900">{item.title}</h3>
                                    <p className="text-gray-500 text-lg leading-relaxed whitespace-pre-line">
                                        {item.desc}
                                    </p>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </section>
            )
        },
        {
            id: 'how-to',
            audioSrc: guideAudio2,
            duration: 17000,
            content: (
                <section className="min-w-screen h-full flex flex-col justify-center items-center relative px-8 z-10 shrink-0">
                    <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center z-10">
                        <motion.div
                            initial={{ opacity: 0, x: -50 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.8 }}
                        >
                            <span className="text-purple-600 font-bold tracking-widest uppercase mb-4 block">User Guide</span>
                            <h2 className="text-6xl font-black mb-8 text-gray-900 leading-[1.1]">
                                간단하게,<br />
                                <span className="text-transparent bg-clip-text bg-linear-to-r from-purple-600 to-indigo-600">시작하세요.</span>
                            </h2>
                            <p className="text-2xl text-gray-600 font-medium leading-relaxed max-w-md">
                                복잡한 절차 없이 세 단계만으로.<br />
                                쇼핑의 새로운 기준을 제시합니다.
                            </p>
                        </motion.div>

                        <div className="space-y-6">
                            {[
                                { num: "01", text: "모드 선택", desc: "사용자에게 가장 편안한 쇼핑 방식을 선택하세요." },
                                { num: "02", text: "음성 대화", desc: "목소리로 상품을 찾고 설명을 들어보세요." },
                                { num: "03", text: "간편 구매", desc: "결제까지 대화하듯 자연스럽게 완료됩니다." }
                            ].map((step, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.2 }}
                                    className="flex items-center gap-6 p-8 rounded-3xl bg-white/80 backdrop-blur-sm shadow-xl shadow-purple-100/50 border border-white/50"
                                >
                                    <span className="text-4xl font-black text-purple-300">{step.num}</span>
                                    <div>
                                        <h4 className="text-xl font-bold text-gray-900 mb-1">{step.text}</h4>
                                        <p className="text-gray-500">{step.desc}</p>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </section>
            )
        },
        {
            id: 'cta',
            audioSrc: guideAudio3,
            duration: 8000,
            content: (
                <section className="min-w-screen h-full flex flex-col justify-center items-center relative px-6 z-10 bg-[#0f0d15] text-white shrink-0">
                    <div className="text-center z-10">
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6 }}
                        >
                            <h2 className="text-6xl md:text-7xl font-black mb-20 tracking-tight" style={{ fontFamily: 'Outfit' }}>
                                <span className="block opacity-30 text-xl font-bold mb-3 tracking-[0.2em] uppercase">Ready to go?</span>
                                <span className="text-white">HearBe와 함께</span>
                            </h2>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 15 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2, duration: 0.6 }}
                            className="relative group"
                        >
                            <div className="absolute inset-0 bg-purple-600/30 blur-[60px] rounded-full scale-150 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                            <div className="absolute inset-0 bg-indigo-600/20 blur-2xl rounded-full scale-125 opacity-20 group-hover:opacity-40 transition-opacity duration-700 pointer-events-none" />

                            <button
                                onClick={goToMain}
                                className="relative cursor-pointer px-16 py-6 rounded-full bg-white text-[#0f0d15] font-black text-xl hover:shadow-[0_15px_40px_rgba(255,255,255,0.2),0_0_60px_rgba(124,58,237,0.3)] hover:-translate-y-1 active:scale-95 transition-all duration-500 overflow-hidden"
                                style={{ fontFamily: 'Outfit' }}
                            >
                                <span className="relative z-10">쇼핑 시작하기</span>
                            </button>
                        </motion.div>
                        <p className="mt-16 text-white/10 text-xs tracking-widest uppercase">© 2026 HearBe</p>
                    </div>
                </section>
            )
        }
    ];

    const totalSteps = GUIDE_STEPS.length;

    useEffect(() => {
        if (timerRef.current) return;

        const stepData = GUIDE_STEPS[currentStep];

        const handleMove = () => {
            if (!isMountedRef.current) return;
            if (currentStep < totalSteps - 1) {
                setCurrentStep(prev => prev + 1);
            } else {
                navigate('/main');
            }
        };

        if (currentStep < totalSteps - 1) {
            timerRef.current = setTimeout(() => {
                handleMove();
            }, stepData.duration);
        }

        if (stepData.audioSrc) {
            const audio = new Audio(stepData.audioSrc);
            audioRef.current = audio;
            audio.play().catch(e => {
            });
        }

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
    }, [currentStep, navigate]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.code === 'Space' || e.key === ' ') {
                e.preventDefault();
                if (currentStep === totalSteps - 1) {
                    goToMain();
                } else {
                    handleNext();
                }
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [currentStep]);

    const handleNext = () => {
        if (currentStep < totalSteps - 1) setCurrentStep(prev => prev + 1);
    };

    const handlePrev = () => {
        if (currentStep > 0) setCurrentStep(prev => prev - 1);
    };

    return (
        <div className="relative w-full h-screen overflow-hidden bg-white selection:bg-purple-200">
            <WaveBackground />

            <header className="fixed top-0 left-0 right-0 z-50 bg-transparent h-32 flex items-center">
                <div className="max-w-7xl w-full mx-auto px-8 flex items-center justify-between">
                    <img
                        src={logoC}
                        alt="HearBe"
                        className="h-24 object-contain cursor-pointer opacity-90 hover:opacity-100 transition-opacity"
                        onClick={() => setCurrentStep(0)}
                    />
                    <button
                        onClick={goToMain}
                        className="cursor-pointer absolute top-10 right-10 px-6 py-2 rounded-full bg-gray-100/80 backdrop-blur-sm border border-gray-200 text-gray-500 text-[14px] font-semibold hover:bg-gray-200 hover:text-gray-800 transition-all duration-300 z-50 shadow-sm"
                    >
                        skip
                    </button>
                </div>
            </header>

            {/* Slider Container */}
            <div
                className="flex w-full h-full transition-transform duration-1000 ease-in-out will-change-transform"
                style={{ transform: `translateX(-${currentStep * 100}vw)` }}
            >
                {GUIDE_STEPS.map((step) => (
                    <div key={step.id} className="w-screen h-full shrink-0">
                        {step.content}
                    </div>
                ))}
            </div>

            {/* Bottom Controls */}
            <div className="fixed bottom-12 left-1/2 transform -translate-x-1/2 flex items-center gap-6 z-50">
                <button
                    onClick={handlePrev}
                    disabled={currentStep === 0}
                    className={`cursor-pointer p-3 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-gray-600 transition-all ${currentStep === 0 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-white hover:text-purple-600 hover:scale-110 shadow-lg'}`}
                >
                    <ChevronDown className="rotate-90" size={20} />
                </button>

                <div className="flex gap-3">
                    {GUIDE_STEPS.map((_, i) => (
                        <button
                            key={i}
                            onClick={() => setCurrentStep(i)}
                            className={`h-2 rounded-full transition-all duration-500 cursor-pointer ${i === currentStep ? 'w-12 bg-purple-600' : 'w-2 bg-gray-300 hover:bg-purple-300'}`}
                        />
                    ))}
                </div>

                <button
                    onClick={handleNext}
                    disabled={currentStep === totalSteps - 1}
                    className={`cursor-pointer p-3 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-gray-600 transition-all ${currentStep === totalSteps - 1 ? 'opacity-30 cursor-not-allowed' : 'hover:bg-white hover:text-purple-600 hover:scale-110 shadow-lg'}`}
                >
                    <ChevronRight size={20} />
                </button>
            </div>
        </div>
    );
};

export default BrandLanding;
