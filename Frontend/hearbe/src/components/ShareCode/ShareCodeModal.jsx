import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import './ShareCodeModal.css';

/**
 * 공유 코드 모달 (A형용)
 * 회의 코드를 표시하고 화면 공유를 시작합니다.
 */
const ShareCodeModal = ({ isOpen, onClose, onStart, shareCode, isLoading }) => {
    if (!isOpen) return null;

    const handleStart = () => {
        onStart();
    };

    const handleCopy = () => {
        if (shareCode) {
            navigator.clipboard.writeText(shareCode);
            alert('코드가 복사되었습니다!');
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content share-code-modal" onClick={(e) => e.stopPropagation()}>
                <h2 className="modal-title">회의 코드</h2>

                {isLoading ? (
                    <div className="loading-spinner">코드 생성 중...</div>
                ) : (
                    <>
                        <div className="code-display">
                            <div className="code-number">{shareCode || '----'}</div>
                            {shareCode && (
                                <button className="copy-button" onClick={handleCopy}>
                                    📋 복사
                                </button>
                            )}
                        </div>

                        <p className="code-instruction">이 코드를 상대방에게 알려주세요</p>

                        <div className="modal-buttons">
                            <button className="btn-cancel" onClick={onClose}>
                                취소
                            </button>
                            <button
                                className="btn-start"
                                onClick={handleStart}
                                disabled={!shareCode}
                            >
                                입장
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

ShareCodeModal.propTypes = {
    isOpen: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onStart: PropTypes.func.isRequired,
    shareCode: PropTypes.string,
    isLoading: PropTypes.bool
};

export default ShareCodeModal;
