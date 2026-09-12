import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import PatientLogin from './pages/PatientLogin';
import DoctorLogin from './pages/DoctorLogin';
import ChatWindow from './components/Chatbot/ChatWindow';
import PatientBookingsPage from './pages/PatientBookingsPage';
import DoctorDashboardPage from './pages/DoctorDashboardPage';

function AppContent() {
  const { role, isAuthenticated } = useAuth();
  const [currentPortal, setCurrentPortal] = useState('patient'); // 'patient' or 'doctor'
  const [activeTab, setActiveTab] = useState('patient-chat');

  useEffect(() => {
    if (isAuthenticated) {
      if (role === 'doctor') {
        setActiveTab('doctor-dashboard');
      } else {
        setActiveTab('patient-chat');
      }
    }
  }, [isAuthenticated, role]);

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentPortal={currentPortal}
        setCurrentPortal={setCurrentPortal}
      />

      <main className="main-content">
        {!isAuthenticated ? (
          currentPortal === 'patient' ? (
            <PatientLogin onSwitchToDoctor={() => setCurrentPortal('doctor')} />
          ) : (
            <DoctorLogin onSwitchToPatient={() => setCurrentPortal('patient')} />
          )
        ) : role === 'doctor' ? (
          <DoctorDashboardPage />
        ) : (
          <>
            {activeTab === 'patient-chat' && (
              <ChatWindow onNavigateToBookings={() => setActiveTab('patient-bookings')} />
            )}
            {activeTab === 'patient-bookings' && (
              <PatientBookingsPage onGoToChat={() => setActiveTab('patient-chat')} />
            )}
          </>
        )}
      </main>

      <footer style={{
        background: '#ffffff',
        borderTop: '1px solid var(--slate-200)',
        padding: '20px 16px',
        textAlign: 'center',
        fontSize: '13px',
        color: 'var(--slate-500)'
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <strong>Cliniq AI Agent</strong> — Autonomous Clinical Scheduling & Practice Management
          </div>
          <div>
            Single-Doctor Practice Engine • Deterministic FSM • Zero-LLM Architecture
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
