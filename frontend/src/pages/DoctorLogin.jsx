import React, { useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Stethoscope, Lock, Phone, ArrowRight } from 'lucide-react';

export default function DoctorLogin({ onSwitchToPatient }) {
  const { login } = useAuth();
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await api.doctorLogin({
        phone_number: phoneNumber,
        password: password
      });
      login(res.access_token, res.role, res.user);
    } catch (err) {
      setError(err.message || 'Invalid doctor credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoDoctorFill = () => {
    setPhoneNumber('9876543210');
    setPassword('doctor123');
  };

  return (
    <div style={{ maxWidth: '440px', margin: '40px auto' }}>
      <div className="card" style={{ padding: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div className="logo-badge" style={{ margin: '0 auto 12px auto', background: 'linear-gradient(135deg, #0369a1, #0f172a)' }}>
            <Stethoscope size={24} />
          </div>
          <h2>Doctor CRM Portal</h2>
          <p style={{ fontSize: '14px', color: 'var(--slate-500)', marginTop: '4px' }}>
            Practitioner Login for Dr. Joseph Varghese
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
          <div className="form-group">
            <label className="form-label">Doctor Phone Number</label>
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
            {loading ? 'Authenticating...' : 'Sign In to Practice CRM'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--slate-200)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            type="button"
            className="btn-outline"
            style={{ fontSize: '12px', padding: '6px 10px' }}
            onClick={handleDemoDoctorFill}
          >
            ⚡ Fill Doctor Demo
          </button>

          <button
            type="button"
            onClick={onSwitchToPatient}
            style={{ color: 'var(--slate-500)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', textDecoration: 'underline' }}
          >
            ← Patient Portal Login
          </button>
        </div>
      </div>
    </div>
  );
}
