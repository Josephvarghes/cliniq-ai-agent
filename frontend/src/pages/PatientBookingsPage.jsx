import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Calendar, Clock, Stethoscope, FileText, CheckCircle, AlertCircle, RefreshCw, XCircle } from 'lucide-react';

export default function PatientBookingsPage({ onGoToChat }) {
  const { user } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  const loadBookings = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getPatientBookings(user.id, statusFilter);
      setBookings(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load bookings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.id) {
      loadBookings();
    }
  }, [user?.id, statusFilter]);

  const handleDirectCancel = async (bookingId, dbId) => {
    if (!window.confirm(`Are you sure you want to cancel booking ${bookingId}?`)) return;

    try {
      await api.cancelAppointment(dbId);
      setActionSuccess(`Appointment ${bookingId} has been successfully cancelled.`);
      loadBookings();
      setTimeout(() => setActionSuccess(''), 5000);
    } catch (err) {
      alert(`Could not cancel appointment: ${err.message}`);
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2>My Appointments</h2>
          <p style={{ color: 'var(--slate-500)', fontSize: '14px', marginTop: '2px' }}>
            View, track, and manage your consultations with Dr. Joseph Varghese
          </p>
        </div>

        <button className="btn-primary" onClick={onGoToChat}>
          <Calendar size={16} /> Book New via Bot
        </button>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {[
          { label: 'All Bookings', val: '' },
          { label: 'Confirmed', val: 'booked' },
          { label: 'Rescheduled', val: 'rescheduled' },
          { label: 'Cancelled', val: 'cancelled' }
        ].map((f) => (
          <button
            key={f.val}
            className={`btn-outline ${statusFilter === f.val ? 'active' : ''}`}
            style={{
              padding: '6px 14px',
              fontSize: '13px',
              background: statusFilter === f.val ? 'var(--primary-600)' : '#fff',
              color: statusFilter === f.val ? '#fff' : 'var(--slate-700)',
              borderColor: statusFilter === f.val ? 'var(--primary-600)' : 'var(--slate-300)'
            }}
            onClick={() => setStatusFilter(f.val)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {actionSuccess && (
        <div style={{
          background: '#dcfce7',
          border: '1px solid #86efac',
          color: '#15803d',
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          fontSize: '14px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <CheckCircle size={18} /> {actionSuccess}
        </div>
      )}

      {error && (
        <div style={{ background: '#fee2e2', color: '#b91c1c', padding: '14px', borderRadius: '8px', marginBottom: '20px' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--slate-500)' }}>
          Loading your appointments...
        </div>
      ) : bookings.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <div style={{ fontSize: '40px', marginBottom: '12px' }}>📅</div>
          <h3>No Appointments Found</h3>
          <p style={{ color: 'var(--slate-500)', fontSize: '14px', maxWidth: '400px', margin: '8px auto 20px' }}>
            {statusFilter
              ? `You have no appointments with status '${statusFilter}'.`
              : 'You have not scheduled any appointments yet. Our AI assistant is ready to help you book in under a minute!'}
          </p>
          <button className="btn-primary" onClick={onGoToChat}>
            Start Booking Assistant
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {bookings.map((b) => (
            <div key={b.id} className="card" style={{ padding: '20px 24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                    <span style={{ fontFamily: 'monospace', fontWeight: '700', fontSize: '15px', color: 'var(--primary-700)' }}>
                      {b.booking_id}
                    </span>
                    <span className={`badge ${b.status}`}>{b.status}</span>
                  </div>
                  <h3 style={{ fontSize: '18px', margin: '4px 0' }}>
                    {b.appointment_type_name || 'Consultation'}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--slate-600)', fontSize: '13px' }}>
                    <Stethoscope size={14} /> {b.doctor_name || 'Dr. Joseph Varghese'}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '15px', fontWeight: '700', color: 'var(--slate-800)' }}>
                    <Calendar size={16} style={{ color: 'var(--primary-600)' }} />
                    {new Date(b.date + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: 'var(--slate-600)', justifyContent: 'flex-end', marginTop: '4px' }}>
                    <Clock size={14} /> {b.time_slot}
                  </div>
                </div>
              </div>

              {b.notes && (
                <div style={{ marginTop: '14px', padding: '8px 12px', background: '#f8fafc', borderRadius: '6px', fontSize: '13px', color: 'var(--slate-600)' }}>
                  <strong>Notes:</strong> {b.notes}
                </div>
              )}

              {b.status !== 'cancelled' && (
                <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--slate-200)', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button
                    className="btn-outline"
                    style={{ fontSize: '13px', padding: '6px 12px' }}
                    onClick={onGoToChat}
                    title="Open Chatbot to Reschedule"
                  >
                    <RefreshCw size={14} /> Reschedule via Bot
                  </button>
                  <button
                    className="btn-danger"
                    style={{ fontSize: '13px', padding: '6px 12px' }}
                    onClick={() => handleDirectCancel(b.booking_id, b.id)}
                  >
                    <XCircle size={14} /> Cancel
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
