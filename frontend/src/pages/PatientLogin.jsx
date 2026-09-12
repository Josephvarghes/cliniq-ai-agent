import React, { useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Stethoscope, User, Lock, Phone, Mail, ArrowRight, CheckCircle } from 'lucide-react';

export default function PatientLogin({ onSwitchToDoctor }) {
  const { login } = useAuth();
  const [isSignup, setIsSignup] = useState(false);

  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isSignup) {
        const res = await api.patientSignup({
          full_name: fullName,
          phone_number: phoneNumber,
          password: password,
          email: email
        });
        login(res.access_token, res.role, res.user);
      } else {
        const res = await api.patientLogin({
          phone_number: phoneNumber,
          password: password
        });
        login(res.access_token, res.role, res.user);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = () => {
    setIsSignup(false);
    setPhoneNumber('9112233445');
    setPassword('patient_pass_123');
  };

  return (
    <div style={{ maxWidth: '440px', margin: '40px auto' }}>
      <div className="card" style={{ padding: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div className="logo-badge" style={{ margin: '0 auto 12px auto' }}>
            <Stethoscope size={24} />
          </div>
          <h2>{isSignup ? 'Create Patient Account' : 'Patient Sign In'}</h2>
          <p style={{ fontSize: '14px', color: 'var(--slate-500)', marginTop: '4px' }}>
            {isSignup
              ? 'Register to book appointments with Dr. Joseph Varghese'
              : 'Enter your phone number to access your booking assistant'}
          </p>
        </div>

        {error && (
          <div style={{
            background: '#fee2e2',
            border: '1px solid #fca5a5',
            color: '#b91c1c',
            padding: '10px 14px',
            borderRadius: '8px',
            fontSize: '13px',
            marginBottom: '16px'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {isSignup && (
            <>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Sarah Jenkins"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Email Address (for confirmations)</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="email"
                    className="form-input"
                    placeholder="sarah@example.com"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>
            </>
          )}

          <div className="form-group">
            <label className="form-label">Phone Number</label>
            <input
              type="tel"
              className="form-input"
              placeholder="e.g. 9876543210"
              required
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            style={{ width: '100%', marginTop: '8px', padding: '12px' }}
            disabled={loading}
          >
            {loading ? 'Processing...' : (isSignup ? 'Register & Continue' : 'Sign In')}
            <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '13px' }}>
          {isSignup ? (
            <span>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => setIsSignup(false)}
                style={{ color: 'var(--primary-600)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700 }}
              >
                Sign In
              </button>
            </span>
          ) : (
            <span>
              New patient?{' '}
              <button
                type="button"
                onClick={() => setIsSignup(true)}
                style={{ color: 'var(--primary-600)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 700 }}
              >
                Create Account
              </button>
            </span>
          )}
        </div>

        <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--slate-200)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            type="button"
            className="btn-outline"
            style={{ fontSize: '12px', padding: '6px 10px' }}
            onClick={handleDemoFill}
          >
            ⚡ Fill Demo Patient
          </button>

          <button
            type="button"
            onClick={onSwitchToDoctor}
            style={{ color: 'var(--slate-500)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', textDecoration: 'underline' }}
          >
            Doctor CRM Login →
          </button>
        </div>
      </div>
    </div>
  );
}
