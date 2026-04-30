import { useState, useEffect, useRef } from 'react';
import Peer from 'peerjs';
import { PEER_CONFIG } from '../../config/peerConfig';

export const usePeerView = () => {
    const [remoteStream, setRemoteStream] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState(null);

    const peerRef = useRef(null);
    const myAudioStreamRef = useRef(null);
    const currentCallRef = useRef(null);
    const connRef = useRef(null);
    const isConnectingRef = useRef(false); // 중복 연결 방지

    const joinSession = async (code) => {
        if (isConnectingRef.current || isConnected || peerRef.current) {
            return;
        }

        isConnectingRef.current = true;

        try {
            setError(null);

            try {
                const audioStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
                myAudioStreamRef.current = audioStream;
            } catch (e) {
            }

            const peerId = `share-${code}-guardian`;
            const newPeer = new Peer(peerId, PEER_CONFIG);
            peerRef.current = newPeer;

            newPeer.on("open", () => {
                const userId = `share-${code}-user`;
                const conn = newPeer.connect(userId, { reliable: true });
                connRef.current = conn;

                conn.on('error', () => {
                    setError('사용자를 찾을 수 없습니다.');
                    isConnectingRef.current = false;
                });

                // 10초 타임아웃
                setTimeout(() => {
                    if (!isConnected && isConnectingRef.current) {
                        setError('사용자로부터 응답이 없습니다.');
                    }
                }, 10000);
            });

            newPeer.on("call", (call) => {
                call.answer(myAudioStreamRef.current);
                currentCallRef.current = call;

                call.on("stream", (stream) => {
                    setRemoteStream(stream);
                    setIsConnected(true);
                    isConnectingRef.current = false;
                });

                call.on("close", () => { leave(); });

                call.on("error", (e) => {
                    setError(`통화 에러: ${e.message}`);
                });
            });

            newPeer.on("error", (err) => {
                setError(err.message);
                if (err.type === 'peer-unavailable') {
                    setError('사용자가 접속하지 않았거나 코드가 잘못되었습니다.');
                    leave();
                }
                isConnectingRef.current = false;
            });

        } catch (err) {
            setError(err.message);
            isConnectingRef.current = false;
            leave();
            throw err;
        }
    };

    const leave = () => {
        isConnectingRef.current = false;

        if (myAudioStreamRef.current) {
            myAudioStreamRef.current.getTracks().forEach(t => t.stop());
            myAudioStreamRef.current = null;
        }
        if (currentCallRef.current) {
            currentCallRef.current.close();
            currentCallRef.current = null;
        }
        if (connRef.current) {
            connRef.current.close();
            connRef.current = null;
        }
        if (peerRef.current) {
            peerRef.current.destroy();
            peerRef.current = null;
        }
        setRemoteStream(null);
        setIsConnected(false);
    };

    useEffect(() => {
        return () => { leave(); };
    }, []);

    return { remoteStream, isConnected, error, joinSession, leave };
};
