import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { useState, useRef } from 'react';

import MainLanding from '../pages/Main/MainLanding';
import BrandLanding from '../pages/Brand/BrandLanding';
import InitialSetup from '../pages/InitialSetup/InitialSetup';
import Intro from '../pages/Intro/Intro';
import AudioPage from '../pages/Audio/AudioPage';

import LoginB from '../pages/Login/LoginB';
import SignUpB from '../pages/SignUp/SignUpB';
import SelectMallB from '../pages/SelectMall/SelectMallB';
import StoreBrowserB from '../pages/StoreBrowser/StoreBrowserB';
import CartB from '../pages/Cart/CartB';
import MemberInfoB from '../pages/MemberInfo/MemberInfoB';
import OrderHistoryB from '../pages/OrderHistory/OrderHistoryB';
import WishlistB from '../pages/Wishlist/WishlistB';
import CardManagementB from '../pages/CardManagement/CardManagementB';
import FindIdB from '../pages/FindId/FindIdB';
import FindPasswordB from '../pages/FindPassword/FindPasswordB';
import ChangePasswordB from '../pages/FindPassword/ChangePasswordB';

import LoginC from '../pages/Login/LoginC';
import SignUpC from '../pages/SignUp/SignUpC';
import SelectMallC from '../pages/SelectMall/SelectMallC';
import CartC from '../pages/Cart/CartC';
import MemberInfoC from '../pages/MemberInfo/MemberInfoC';
import OrderHistoryC from '../pages/OrderHistory/OrderHistoryC';
import WishlistC from '../pages/Wishlist/WishlistC';
import FindIdC from '../pages/FindId/FindIdC';
import FindPasswordC from '../pages/FindPassword/FindPasswordC';

import GuardianViewS from '../pages/GuardianView/GuardianViewS';

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [showInitialSetup, setShowInitialSetup] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('app') === 'mcp') {
      localStorage.setItem('hearbe_mcp_setup_completed', 'true');
      return false;
    }
    return localStorage.getItem('hearbe_mcp_setup_completed') !== 'true';
  });
  const modeSelectionRef = useRef(null);

  const handleModeSelect = (mode) => {
    const accessToken = localStorage.getItem('accessToken');
    if (mode === 'common') {
      navigate(accessToken ? '/C/mall' : '/C/login');
    } else if (mode === 'sharing') {
      navigate('/S/join');
    } else if (mode === 'big') {
      navigate(accessToken ? '/B/mall' : '/B/login');
    } else {
      navigate('/A');
    }
  };

  if (showInitialSetup && (location.pathname === '/main' || location.pathname === '/intro' || location.pathname === '/')) {
    return <InitialSetup onComplete={() => setShowInitialSetup(false)} />;
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/intro" replace />} />
      <Route path="/intro" element={<Intro />} />
      <Route path="/guide" element={<BrandLanding />} />
      <Route
        path="/main"
        element={
          <MainLanding
            handleModeSelect={handleModeSelect}
            modeSelectionRef={modeSelectionRef}
            onOpenSetup={() => setShowInitialSetup(true)}
          />
        }
      />

      <Route path="/A/*" element={<AudioPage />} />

      <Route path="/B/login" element={<LoginB />} />
      <Route path="/B/signup" element={<SignUpB />} />
      <Route path="/B/mall" element={<SelectMallB />} />
      <Route path="/B/store" element={<StoreBrowserB />} />
      <Route path="/B/cart" element={<CartB />} />
      <Route path="/B/member-info" element={<MemberInfoB />} />
      <Route path="/B/order-history" element={<OrderHistoryB />} />
      <Route path="/B/wishlist" element={<WishlistB />} />
      <Route path="/B/card-management" element={<CardManagementB />} />
      <Route path="/B/findId" element={<FindIdB />} />
      <Route path="/B/findPassword" element={<FindPasswordB />} />
      <Route path="/B/changePassword" element={<ChangePasswordB />} />

      <Route path="/C/login" element={<LoginC />} />
      <Route path="/C/signup" element={<SignUpC />} />
      <Route path="/C/findId" element={<FindIdC />} />
      <Route path="/C/findPassword" element={<FindPasswordC />} />
      <Route path="/C/mall" element={<SelectMallC />} />
      <Route path="/C/order-history" element={<OrderHistoryC />} />
      <Route path="/C/wishlist" element={<WishlistC />} />
      <Route path="/C/member-info" element={<MemberInfoC />} />
      <Route path="/C/mypage" element={<Navigate to="/C/member-info" replace />} />
      <Route path="/C/cart" element={<CartC />} />

      <Route path="/S/join" element={<GuardianViewS />} caseSensitive={false} />

      <Route path="*" element={<Navigate to="/intro" replace />} />
    </Routes>
  );
}

export default function AppRouter() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppContent />
    </BrowserRouter>
  );
}
