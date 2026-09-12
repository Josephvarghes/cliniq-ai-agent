import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Stethoscope, Calendar, MessageSquare, LayoutDashboard, LogOut, Clock, Activity, ShieldAlert } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, currentPortal, setCurrentPortal }) {
  const { user, role, logout, isAuthenticated } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="brand-logo" onClick={() => setActiveTab(role === 'doctor' ? 'doctor-dashboard' : 'patient-chat')}>
          <div className="logo-badge">
            <Stethoscope size={22} />
          </div>
          <div>
            <div className="brand-text">Cliniq AI</div>
            <span className="brand-sub">
              {role === 'doctor' ? 'Doctor CRM Portal' : 'Patient Assistant'}
            </span>
          </div>
        </div>

        <nav className="nav-actions">
          {isAuthenticated && role === 'patient' && (
            <>
              <button
                className={`nav-link-btn ${activeTab === 'patient-chat' ? 'active' : ''}`}
                onClick={() => setActiveTab('patient-chat')}
              >
                <MessageSquare size={16} /> Booking Bot
              </button>
              <button
                className={`nav-link-btn ${activeTab === 'patient-bookings' ? 'active' : ''}`}
                onClick={() => setActiveTab('patient-bookings')}
              >
                <Calendar size={16} /> My Bookings
              </button>
            </>
          )}

          {isAuthenticated && role === 'doctor' && (
            <>
              <button
                className={`nav-link-btn ${activeTab === 'doctor-dashboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('doctor-dashboard')}
              >
                <LayoutDashboard size={16} /> Queue & Dashboard
              </button>
              <button
                className={`nav-link-btn ${activeTab === 'doctor-schedule' ? 'active' : ''}`}
                onClick={() => setActiveTab('doctor-schedule')}
              >
                <Clock size={16} /> Schedule
              </button>
              <button
                className={`nav-link-btn ${activeTab === 'doctor-insights' ? 'active' : ''}`}
                onClick={() => setActiveTab('doctor-insights')}
              >
                <Activity size={16} /> Insights
              </button>
            </>
          )}

          {isAuthenticated ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: '12px' }}>
              <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--slate-600)' }}>
                {user?.full_name}
              </span>
              <button className="nav-link-btn" onClick={logout} title="Sign Out">
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className={`nav-link-btn ${currentPortal === 'patient' ? 'active' : ''}`}
                onClick={() => setCurrentPortal('patient')}
              >
                Patient Portal
              </button>
              <button
                className={`nav-link-btn ${currentPortal === 'doctor' ? 'active' : ''}`}
                onClick={() => setCurrentPortal('doctor')}
              >
                Doctor CRM
              </button>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
