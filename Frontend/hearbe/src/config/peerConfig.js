export const PEER_CONFIG = {
    host: import.meta.env.VITE_PEER_HOST || "localhost",
    port: import.meta.env.VITE_PEER_PORT ? parseInt(import.meta.env.VITE_PEER_PORT) : 9000,
    path: "/hearbe-peer",
    secure: import.meta.env.VITE_PEER_SECURE === "true",
    config: {
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
    }
};

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8080/api";
