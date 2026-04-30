import { Volume2, Download, Mic, Headphones } from 'lucide-react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Swal from 'sweetalert2';
import './InitialSetup.css';

const STEPS = {
    MCP_DOWNLOAD: 'mcp_download',
    MIC_PERMISSION: 'mic_permission',
    SPEAKER_TEST: 'speaker_test',
    COMPLETED: 'completed',
};

const VOICE_PROGRAM_BASE_NAME = '음성지원프로그램';
const VOICE_PROGRAM_LATEST_FILE = `${VOICE_PROGRAM_BASE_NAME}_latest.zip`;

export default function InitialSetup({ onComplete }) {
    const [currentStep, setCurrentStep] = useState(STEPS.MCP_DOWNLOAD);
    const [micPermissionGranted, setMicPermissionGranted] = useState(false);
    const [voiceProgramVersion, setVoiceProgramVersion] = useState('');

    useEffect(() => {
        const loadVoices = () => window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = loadVoices;
        loadVoices();
    }, []);

    useEffect(() => {
        if (currentStep === STEPS.COMPLETED) {
            onComplete(true);
        }
    }, [currentStep, onComplete]);

    // [최신 기능 통합]: 서버에서 음성 프로그램 최신 버전 정보를 가져옵니다.
    useEffect(() => {
        let mounted = true;
        fetch('/downloads/voice-program-version.json', { cache: 'no-store' })
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
                if (!mounted || !data?.version) return;
                setVoiceProgramVersion(data.version);
            })
            .catch(() => { });
        return () => { mounted = false; };
    }, []);

    const voiceProgramDownloadFile = voiceProgramVersion
        ? `${VOICE_PROGRAM_BASE_NAME}_${voiceProgramVersion}.zip`
        : VOICE_PROGRAM_LATEST_FILE;

    const handleMcpDownload = () => {
        setCurrentStep(STEPS.MIC_PERMISSION);
    };

    const handleMicPermission = async (granted) => {
        if (granted) {
            try {
                await navigator.mediaDevices.getUserMedia({ audio: true });
                setMicPermissionGranted(true);
            } catch (error) {
                console.error('마이크 권한 거부됨', error);
                setMicPermissionGranted(false);
            }
        } else {
            setMicPermissionGranted(false);
        }
        setCurrentStep(STEPS.SPEAKER_TEST);
    };

    const handleSpeakerTest = () => {
        localStorage.setItem('hearbe_mcp_setup_completed', 'true');
        onComplete(micPermissionGranted);
    };

    const handleSpeakerFailure = () => {
        Swal.fire({
            title: '소리가 안 들리시나요?',
            html: '컴퓨터의 **음량 설정**과 **스피커 연결** 상태를 확인해 주세요.<br/>브라우저의 소리가 꺼져있을 수도 있습니다.',
            icon: 'warning',
            confirmButtonText: '다시 시도하기',
            confirmButtonColor: '#7c3aed'
        });
    };

    const playTestSound = () => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance('이 소리가 선명하게 들리시면 잘들림 버튼을 눌러주세요.');

        utterance.lang = 'ko-KR';
        const voices = window.speechSynthesis.getVoices();
        const femaleVoice = voices.find(voice =>
            (voice.lang === 'ko-KR' || voice.lang === 'ko_KR') &&
            (voice.name.includes('Google') || voice.name.includes('Yuna') || voice.name.includes('Heami') || voice.name.includes('Sun-Hi'))
        );

        if (femaleVoice) {
            utterance.voice = femaleVoice;
        }

        utterance.pitch = 1.1;
        utterance.rate = 1.0;

        window.speechSynthesis.speak(utterance);
    };

    if (currentStep === STEPS.COMPLETED) return null;

    return (
        <div className="setup-container">
            <AnimatePresence mode="wait">
                {currentStep === STEPS.MCP_DOWNLOAD && (
                    <motion.div
                        key="step1"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 1.05 }}
                        className="setup-card"
                    >
                        <div className="icon-box">
                            <Download size={48} />
                        </div>
                        <h2 className="setup-title">음성 보조 프로그램 설치</h2>
                        <p className="setup-desc">
                            음성 인식과 원격 음성 제어를 위해<br />
                            보조 프로그램을 설치해 주세요.
                        </p>
                        <div className="btn-group">
                            <button onClick={handleMcpDownload} className="btn-secondary-setup">나중에</button>
                            <a
                                href={encodeURI(`/downloads/${voiceProgramDownloadFile}`)}
                                download={voiceProgramDownloadFile}
                                onClick={handleMcpDownload}
                                className="btn-primary-setup no-underline flex items-center justify-center"
                                style={{ flex: 1.5 }}
                            >
                                지금 다운로드
                            </a>
                        </div>
                    </motion.div>
                )}

                {currentStep === STEPS.MIC_PERMISSION && (
                    <motion.div
                        key="step2"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 1.05 }}
                        className="setup-card"
                    >
                        <div className="icon-box">
                            <Mic size={48} />
                        </div>
                        <h2 className="setup-title">마이크 권한 허용</h2>
                        <p className="setup-desc">
                            HearBe는 음성 명령으로 쇼핑을 돕습니다.<br />
                            원활한 사용을 위해 마이크 권한을 허용해 주세요.
                        </p>
                        <div className="btn-group">
                            <button onClick={() => handleMicPermission(false)} className="btn-secondary-setup">건너뛰기</button>
                            <button onClick={() => handleMicPermission(true)} className="btn-primary-setup">권한 허용하기</button>
                        </div>
                    </motion.div>
                )}

                {currentStep === STEPS.SPEAKER_TEST && (
                    <motion.div
                        key="step3"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 1.05 }}
                        className="setup-card"
                    >
                        <div className="icon-box pulse">
                            <Headphones size={48} />
                        </div>
                        <h2 className="setup-title">스피커 확인</h2>
                        <p className="setup-desc">
                            안내 음성이 잘 들리는지 확인해 주세요.
                        </p>

                        <button onClick={playTestSound} className="test-sound-btn">
                            <Volume2 size={24} />
                            소리 재생하기
                        </button>

                        <div className="btn-group">
                            <button onClick={handleSpeakerFailure} className="btn-secondary-setup">안 들려요</button>
                            <button onClick={handleSpeakerTest} className="btn-primary-setup">잘 들려요</button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
