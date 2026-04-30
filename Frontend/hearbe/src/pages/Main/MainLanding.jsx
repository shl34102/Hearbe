import { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Volume2, Download, ArrowRight, Share2, Layout, Zap, Info, BookOpen, Eye, Sparkles } from 'lucide-react';
import '../../App.css';
import '../../index.css'
import logoC from '../../assets/logoC.png';

const VOICE_PROGRAM_BASE_NAME = '음성지원프로그램';
const VOICE_PROGRAM_LATEST_FILE = `${VOICE_PROGRAM_BASE_NAME}_latest.zip`;

const ModeCard = ({ mode, onSelect }) => (
    <motion.button
        whileHover={{ y: -15, scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => onSelect(mode.id, mode.title)}
        className="cursor-pointer relative overflow-hidden group rounded-[3rem] shadow-xl hover:shadow-[0_40px_80px_rgba(0,0,0,0.08)] transition-all duration-500 w-full h-[540px] flex flex-col items-start justify-between p-10 text-left bg-white border border-gray-100/50"
        style={{ background: mode.bgColor }}
    >
        {/* Background Icon Decor */}
        <div className="absolute -right-16 -bottom-16 opacity-[0.08] transition-all duration-700 group-hover:scale-125 group-hover:rotate-12 group-hover:opacity-[0.12] pointer-events-none">
            {mode.iconLarge}
        </div>

        {/* Shimmer Effect */}
        <div className="absolute inset-0 bg-linear-to-tr from-white/0 via-white/10 to-white/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 pointer-events-none" />

        {/* Top Content */}
        <div className="relative z-10 w-full">
            <div className="w-20 h-20 rounded-3xl bg-white/20 backdrop-blur-2xl flex items-center justify-center mb-10 text-white shadow-[inset_0_0_20px_rgba(255,255,255,0.2)] border border-white/30 group-hover:scale-110 transition-transform duration-500">
                {mode.icon}
            </div>

            <div className="inline-block px-4 py-1.5 rounded-full mb-8 backdrop-blur-md border border-white/20" style={{ backgroundColor: mode.badgeBg || 'rgba(255,255,255,0.2)' }}>
                <span className="text-[10px] font-black tracking-[0.2em] uppercase" style={{ color: mode.labelColor || '#FFFFFF' }}>
                    {mode.label}
                </span>
            </div>

            <h3 className="text-4xl font-black mb-6 leading-tight tracking-tight drop-shadow-sm" style={{ color: mode.textColor || '#FFFFFF' }}>
                {mode.title}
            </h3>

            <p className="text-lg font-medium leading-relaxed opacity-80 max-w-[95%]" style={{ color: mode.textColor || '#FFFFFF' }}>
                {mode.desc}
            </p>
        </div>

        {/* Bottom Content */}
        <div className="relative z-10 w-full mt-auto">
            <div className="flex flex-wrap gap-2.5 mb-10">
                {mode.tags.map(tag => (
                    <span
                        key={tag}
                        className="px-5 py-2 rounded-full text-[13px] font-black border border-white/20 backdrop-blur-md"
                        style={{
                            color: mode.textColor || '#FFFFFF',
                            backgroundColor: 'rgba(255,255,255,0.1)'
                        }}
                    >
                        {tag}
                    </span>
                ))}
            </div>

            <div className="flex items-center justify-between w-full">
                <span className="text-xs font-black uppercase tracking-[0.3em] opacity-60" style={{ color: mode.textColor || '#FFFFFF' }}>
                    Start Shopping
                </span>
                <div
                    className="w-14 h-14 rounded-full flex items-center justify-center shadow-lg group-hover:bg-white transition-all duration-500"
                    style={{ backgroundColor: mode.btnBg || 'rgba(255,255,255,0.2)', color: mode.arrowColor || '#FFFFFF' }}
                >
                    <ArrowRight size={26} strokeWidth={2.5} className="group-hover:translate-x-1 transition-transform" />
                </div>
            </div>
        </div>
    </motion.button>
);


const MainLanding = ({ handleModeSelect, modeSelectionRef, onOpenSetup }) => {
    const navigate = useNavigate();
    const [voiceProgramVersion, setVoiceProgramVersion] = useState('');

    useEffect(() => {
        let mounted = true;

        fetch('/downloads/voice-program-version.json', { cache: 'no-store' })
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (!mounted || !data?.version) return;
                setVoiceProgramVersion(data.version);
            })
            .catch(() => {
                // Ignore metadata errors and fallback to latest alias.
            });

        return () => {
            mounted = false;
        };
    }, []);

    const voiceProgramDownloadFile = voiceProgramVersion
        ? `${VOICE_PROGRAM_BASE_NAME}_${voiceProgramVersion}.zip`
        : VOICE_PROGRAM_LATEST_FILE;

    return (
        <div className="w-full min-h-screen bg-[#fcfcfd] flex flex-col items-center justify-start relative overflow-x-hidden landing-container">

            {/* Premium Ambient Background */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className="absolute top-[-15%] left-[-10%] w-[70%] h-[70%] bg-purple-50 rounded-full blur-[160px] opacity-60" />
                <div className="absolute bottom-[-15%] right-[-10%] w-[70%] h-[70%] bg-blue-50 rounded-full blur-[160px] opacity-60" />
            </div>

            {/* Modern Unified Header */}
            <header className="fixed top-0 left-0 right-0 z-50 h-24 flex items-center bg-transparent">
                <div className="max-w-6xl w-full mx-auto px-12 md:px-16 flex items-center justify-between">
                    <img
                        src={logoC} alt="HearBe"
                        className="h-16 md:h-20 object-contain cursor-pointer drop-shadow-sm"
                        onClick={() => navigate('/main')}
                    />
                    <div className="flex items-center gap-4">
                        {[
                            { icon: <Info size={22} />, path: '/intro', label: '서비스 소개' },
                            { icon: <BookOpen size={22} />, path: '/guide', label: '가이드' },
                            {
                                icon: <Download size={22} />,
                                path: encodeURI(`/downloads/${voiceProgramDownloadFile}`),
                                label: '다운로드',
                                isExternal: true
                            }
                        ].map((item, idx) => (
                            <motion.button
                                key={idx}
                                whileHover={{ scale: 1.05, backgroundColor: '#f9fafb' }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => {
                                    if (item.isExternal) {
                                        const link = document.createElement('a');
                                        link.href = item.path;
                                        const rawFileName = item.path.split('/').pop() || '';
                                        link.download = decodeURIComponent(rawFileName);
                                        link.click();
                                    } else {
                                        navigate(item.path);
                                    }
                                }}
                                className="p-3 md:p-3.5 rounded-2xl bg-white border border-gray-100 shadow-sm text-gray-600 hover:text-purple-600 transition-all relative group"
                            >
                                {item.icon}
                                <div className="absolute top-full mt-3 px-3 py-1.5 bg-gray-900 text-white text-[10px] font-bold rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none shadow-2xl z-50">
                                    {item.label}
                                </div>
                            </motion.button>
                        ))}
                    </div>
                </div>
            </header>


            {/* Main Content Area */}
            <main className="relative z-10 w-full max-w-6xl px-12 md:px-16 pt-32 pb-32 flex flex-col items-center">

                {/* Title Section - Perfectly Centered */}
                <div className="w-full text-center mb-16 md:mb-20 relative">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                        className="inline-block relative"
                    >
                        <h2 className="text-5xl md:text-6xl font-black text-[#0f172a] mb-6 tracking-tight">
                            쇼핑 모드 선택
                        </h2>

                        {/* Type S - Clean Premium Chatbot-style Floating Badge */}
                        <div className="absolute -right-36 md:-right-64 top-1/2 -translate-y-1/2 hidden lg:block">
                            <motion.button
                                initial={{ scale: 0, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                whileHover={{
                                    scale: 1.05,
                                    boxShadow: '0 15px 30px rgba(0,0,0,0.05)',
                                    y: -3
                                }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => handleModeSelect('sharing', '공유 쇼핑')}
                                className="relative group p-1"
                            >
                                <div className="relative flex items-center gap-5 bg-white border border-gray-100 pl-4 pr-8 py-4 rounded-full shadow-lg overflow-hidden">
                                    {/* Inner Shimmer */}
                                    <div className="absolute inset-0 bg-linear-to-r from-transparent via-gray-50/50 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />

                                    <div className="w-14 h-14 rounded-full bg-purple-600 text-white flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-500">
                                        <Share2 size={26} strokeWidth={2.5} />
                                    </div>

                                    <div className="flex flex-col items-start text-nowrap">
                                        <span className="text-[10px] font-black text-purple-700 uppercase tracking-[0.2em] leading-none mb-1">TYPE S</span>
                                        <span className="text-lg font-black text-gray-800 tracking-tight">공유 쇼핑 입장</span>
                                    </div>

                                    {/* Indicator Dot */}
                                    <div className="absolute top-4 right-5 w-2 h-2 bg-purple-600 rounded-full">
                                        <div className="absolute inset-0 bg-purple-600 rounded-full animate-ping opacity-75" />
                                    </div>
                                </div>
                            </motion.button>
                        </div>

                        <div className="w-12 h-1 bg-slate-200 mx-auto mb-8 rounded-full" />
                        <p className="text-lg md:text-xl text-gray-400 font-medium tracking-tight max-w-2xl mx-auto px-4 leading-relaxed">
                            사용 환경과 선호도에 맞춰 최적화된 테마를 경험하세요.
                        </p>
                    </motion.div>
                </div>

                {/* 3 Main Mode Grid (A, B, C) */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 md:gap-12 w-full mb-24">
                    <ModeCard
                        onSelect={handleModeSelect}
                        mode={{
                            id: 'audio',
                            label: 'TYPE A',
                            title: '음성 쇼핑',
                            desc: <>목소리만으로 충분한<br />완전 음성 쇼핑 환경</>,
                            tags: ['#음성AI', '#완전접근성'],
                            bgColor: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)',
                            textColor: '#FFFFFF',
                            icon: <Volume2 size={32} strokeWidth={2.5} />,
                            iconLarge: <Zap size={240} strokeWidth={1} />,
                            arrowColor: '#3B82F6'
                        }}
                    />

                    <ModeCard
                        onSelect={handleModeSelect}
                        mode={{
                            id: 'big',
                            label: 'TYPE B',
                            title: '고대비 쇼핑',
                            desc: <>선명한 대비와 큰 글씨로<br />가독성을 높인 쇼핑 환경</>,
                            tags: ['#저시력자', '#고성능대비'],
                            bgColor: '#121620',
                            textColor: '#FACC15',
                            labelColor: '#121620',
                            badgeBg: '#FACC15',
                            btnBg: '#FACC15',
                            arrowColor: '#121620',
                            icon: <Eye size={32} strokeWidth={2.5} color="#FACC15" />,
                            iconLarge: <Eye size={240} strokeWidth={0.5} color="#FACC15" />
                        }}
                    />

                    <ModeCard
                        onSelect={handleModeSelect}
                        mode={{
                            id: 'common',
                            label: 'TYPE C',
                            title: '일반 쇼핑',
                            desc: <>음성과 시각의 조화로<br />더 쉽고 편리한 쇼핑 환경</>,
                            tags: ['#음성&시각', '#스마트검색'],
                            bgColor: 'linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%)',
                            textColor: '#FFFFFF',
                            icon: <Layout size={32} strokeWidth={2.5} />,
                            iconLarge: <Layout size={240} strokeWidth={1} />,
                            arrowColor: '#8B5CF6'
                        }}
                    />
                </div>
            </main>

            {/* Original Project Footer */}
            <footer className="landing-footer w-full">
                <p>© 2026 HearBe. All rights reserved.</p>
            </footer>
        </div>
    );
};

export default MainLanding;
