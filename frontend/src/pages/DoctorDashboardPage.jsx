import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import {
  Users, Calendar, Clock, Activity, AlertTriangle, ShieldAlert,
  CheckCircle, RefreshCw, Mail, MessageSquare, Plus, Check
} from 'lucide-react';

export default function DoctorDashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview'); // overview, schedule, insights, emergency
  const [dashboardData, setDashboardData] = useState(null);
  const [scheduleList, setScheduleList] = useState([]);
  const [insightsData, setInsightsData] = useState(null);
  const [insightsRange, setInsightsRange] = useState('monthly');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // New schedule form
  const [schedDate, setSchedDate] = useState('');
  const [schedStart, setSchedStart] = useState('09:00');
  const [schedEnd, setSchedEnd] = useState('17:00');
  const [schedDuration, setSchedDuration] = useState(30);

  // Emergency block form
  const [blockDate, setBlockDate] = useState('');
  const [blockReason, setBlockReason] = useState('Doctor emergency medical leave');
  const [blockResult, setBlockResult] = useState(null);

  const loadAllData = async () => {
    if (!user?.id) return;
    setLoading(true);
    setError('');
    try {
      const [dash, sched, ins] = await Promise.all([
        api.getDoctorDashboard(user.id),
        api.getDoctorSchedule(user.id),
        api.getDoctorInsights(user.id, insightsRange)
      ]);
      setDashboardData(dash);
      setScheduleList(sched || []);
      setInsightsData(ins);
    } catch (err) {
      setError(err.message || 'Failed to load doctor CRM data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, [user?.id, insightsRange]);

  const handleCreateSchedule = async (e) => {
    e.preventDefault();
    if (!schedDate) return;
    try {
      await api.createDoctorSchedule(user.id, {
        date: schedDate,
        start_time: schedStart,
        end_time: schedEnd,
        slot_duration_minutes: parseInt(schedDuration)
      });
      setSuccessMsg(`Availability successfully added for ${schedDate}.`);
      setSchedDate('');
      loadAllData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      alert(`Error creating schedule: ${err.message}`);
    }
  };

  const handleEmergencyBlock = async (e) => {
    e.preventDefault();
    if (!blockDate) return;
    if (!window.confirm(`Are you sure you want to block all slots on ${blockDate}? All booked patients will automatically receive emergency reschedule emails.`)) {
      return;
    }

    try {
      const res = await api.emergencyBlockSchedule(user.id, {
        date: blockDate,
        reason: blockReason
      });
      setBlockResult(res);
      setSuccessMsg(res.message);
      loadAllData();
    } catch (err) {
      alert(`Error applying emergency block: ${err.message}`);
    }
  };

  if (loading && !dashboardData) {
    return (
      <div style={{ textAlign: 'center', padding: '60px', color: 'var(--slate-500)' }}>
        Loading Doctor CRM Control Center...
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
      {/* Doctor Header Banner */}
      <div className="card" style={{ marginBottom: '24px', background: 'linear-gradient(135deg, #075985 0%, #0c4a6e 100%)', color: '#fff', border: 'none' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <span style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px', opacity: 0.85, fontWeight: 700 }}>
              Practice Management CRM
            </span>
            <h2 style={{ color: '#fff', fontSize: '24px', margin: '4px 0' }}>
              {dashboardData?.doctor?.full_name || 'Dr. Joseph Varghese'}
            </h2>
            <p style={{ opacity: 0.9, fontSize: '14px' }}>
              {dashboardData?.doctor?.specialization} • Phone: {dashboardData?.doctor?.phone_number}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px', background: 'rgba(255,255,255,0.1)', padding: '6px', borderRadius: '12px' }}>
            <button
              className={`nav-link-btn ${activeTab === 'overview' ? 'active' : ''}`}
              style={{ color: '#fff', background: activeTab === 'overview' ? 'rgba(255,255,255,0.25)' : 'transparent' }}
              onClick={() => setActiveTab('overview')}
            >
              Queue & Overview
            </button>
            <button
              className={`nav-link-btn ${activeTab === 'schedule' ? 'active' : ''}`}
              style={{ color: '#fff', background: activeTab === 'schedule' ? 'rgba(255,255,255,0.25)' : 'transparent' }}
              onClick={() => setActiveTab('schedule')}
            >
              Schedule
            </button>
            <button
              className={`nav-link-btn ${activeTab === 'insights' ? 'active' : ''}`}
              style={{ color: '#fff', background: activeTab === 'insights' ? 'rgba(255,255,255,0.25)' : 'transparent' }}
              onClick={() => setActiveTab('insights')}
            >
              Insights
            </button>
            <button
              className={`nav-link-btn ${activeTab === 'emergency' ? 'active' : ''}`}
              style={{ color: '#fca5a5', background: activeTab === 'emergency' ? 'rgba(239, 68, 68, 0.3)' : 'transparent' }}
              onClick={() => setActiveTab('emergency')}
            >
              🚨 Emergency Block
            </button>
          </div>
        </div>
      </div>

      {successMsg && (
        <div style={{ background: '#dcfce7', border: '1px solid #86efac', color: '#15803d', padding: '12px 16px', borderRadius: '8px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle size={18} /> {successMsg}
        </div>
      )}

      {error && (
        <div style={{ background: '#fee2e2', color: '#b91c1c', padding: '12px 16px', borderRadius: '8px', marginBottom: '20px' }}>
          {error}
        </div>
      )}

      {/* TAB 1: OVERVIEW & QUEUE */}
      {activeTab === 'overview' && (
        <div>
          {/* Top Metric Cards */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-icon blue"><Calendar size={24} /></div>
              <div>
                <div className="metric-value">{dashboardData?.metrics_summary?.today_active_appointments || 0}</div>
                <div className="metric-label">Today's Consultations</div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon green"><Clock size={24} /></div>
              <div>
                <div className="metric-value">{dashboardData?.metrics_summary?.next_7_days_appointments || 0}</div>
                <div className="metric-label">Next 7 Days Volume</div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon amber"><MessageSquare size={24} /></div>
              <div>
                <div className="metric-value">{dashboardData?.metrics_summary?.pending_enquiries || 0}</div>
                <div className="metric-label">Patient Enquiries</div>
              </div>
            </div>
          </div>

          {/* Today's Consultations Queue */}
          <div className="card" style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>Today's Patient Queue ({dashboardData?.today_date})</h3>
              <button className="btn-outline" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={loadAllData}>
                <RefreshCw size={14} /> Refresh
              </button>
            </div>

            {dashboardData?.today_bookings?.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '32px', color: 'var(--slate-500)' }}>
                No consultations booked for today.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--slate-200)', color: 'var(--slate-500)' }}>
                      <th style={{ padding: '10px 12px' }}>Time Slot</th>
                      <th style={{ padding: '10px 12px' }}>Booking Ref</th>
                      <th style={{ padding: '10px 12px' }}>Patient Name</th>
                      <th style={{ padding: '10px 12px' }}>Phone</th>
                      <th style={{ padding: '10px 12px' }}>Type</th>
                      <th style={{ padding: '10px 12px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardData?.today_bookings?.map((appt) => (
                      <tr key={appt.id} style={{ borderBottom: '1px solid var(--slate-100)' }}>
                        <td style={{ padding: '12px', fontWeight: 700, color: 'var(--primary-700)' }}>
                          {appt.time_slot}
                        </td>
                        <td style={{ padding: '12px', fontFamily: 'monospace' }}>{appt.booking_id}</td>
                        <td style={{ padding: '12px', fontWeight: 600 }}>{appt.patient_name}</td>
                        <td style={{ padding: '12px' }}>{appt.patient_phone}</td>
                        <td style={{ padding: '12px' }}>{appt.appointment_type_name}</td>
                        <td style={{ padding: '12px' }}>
                          <span className={`badge ${appt.status}`}>{appt.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Upcoming Next 7 Days */}
          <div className="card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}>Upcoming Schedule (Next 7 Days)</h3>
            {dashboardData?.upcoming_bookings?.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px', color: 'var(--slate-500)' }}>
                No upcoming bookings in the next 7 days.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                {dashboardData?.upcoming_bookings?.map((b) => (
                  <div key={b.id} style={{ padding: '14px', border: '1px solid var(--slate-200)', borderRadius: '8px', background: '#f8fafc' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontWeight: 700, color: 'var(--primary-700)' }}>{b.date} • {b.time_slot}</span>
                      <span className={`badge ${b.status}`}>{b.status}</span>
                    </div>
                    <div style={{ fontWeight: 600 }}>{b.patient_name}</div>
                    <div style={{ fontSize: '13px', color: 'var(--slate-500)' }}>{b.appointment_type_name} ({b.booking_id})</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Patient Enquiries Inbox */}
          <div className="card">
            <h3 style={{ marginBottom: '16px' }}>Patient Enquiries Inbox (Chatbot Fallback)</h3>
            {dashboardData?.recent_enquiries?.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px', color: 'var(--slate-500)' }}>
                No patient enquiries submitted.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {dashboardData?.recent_enquiries?.map((enq) => (
                  <div key={enq.id} style={{ padding: '14px', border: '1px solid var(--slate-200)', borderRadius: '8px', background: '#fff' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{ fontWeight: 700 }}>{enq.patient_name} ({enq.patient_phone})</span>
                      <span style={{ fontSize: '12px', color: 'var(--slate-400)' }}>
                        {new Date(enq.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: '14px', color: 'var(--slate-700)' }}>{enq.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: SCHEDULE & AVAILABILITY */}
      {activeTab === 'schedule' && (
        <div>
          <div className="card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}>Define Working Hours & Availability</h3>
            <form onSubmit={handleCreateSchedule} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', alignItems: 'flex-end' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Date</label>
                <input
                  type="date"
                  className="form-input"
                  required
                  min={new Date().toISOString().split('T')[0]}
                  value={schedDate}
                  onChange={(e) => setSchedDate(e.target.value)}
                />
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Start Time</label>
                <input
                  type="time"
                  className="form-input"
                  required
                  value={schedStart}
                  onChange={(e) => setSchedStart(e.target.value)}
                />
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">End Time</label>
                <input
                  type="time"
                  className="form-input"
                  required
                  value={schedEnd}
                  onChange={(e) => setSchedEnd(e.target.value)}
                />
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Slot Duration (Minutes)</label>
                <select
                  className="form-input"
                  value={schedDuration}
                  onChange={(e) => setSchedDuration(e.target.value)}
                >
                  <option value={15}>15 minutes</option>
                  <option value={20}>20 minutes</option>
                  <option value={30}>30 minutes</option>
                  <option value={45}>45 minutes</option>
                  <option value={60}>60 minutes</option>
                </select>
              </div>

              <button type="submit" className="btn-primary" style={{ height: '42px' }}>
                <Plus size={16} /> Save Hours
              </button>
            </form>
          </div>

          {/* Configured Schedules List */}
          <div className="card">
            <h3 style={{ marginBottom: '16px' }}>Configured Availability Calendar</h3>
            {scheduleList.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '32px', color: 'var(--slate-500)' }}>
                No custom availability rules configured yet. The system automatically defaults to standard clinic hours (09:00 AM - 05:00 PM).
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '14px' }}>
                {scheduleList.map((s) => (
                  <div
                    key={s.id}
                    style={{
                      padding: '16px',
                      border: s.is_blocked ? '1.5px solid #fda4af' : '1px solid var(--slate-200)',
                      borderRadius: '8px',
                      background: s.is_blocked ? '#fff1f2' : '#ffffff'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 700, fontSize: '15px' }}>{s.date}</span>
                      <span className={`badge ${s.is_blocked ? 'cancelled' : 'completed'}`}>
                        {s.is_blocked ? 'BLOCKED' : 'AVAILABLE'}
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--slate-600)' }}>
                      Hours: {s.start_time} - {s.end_time}
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--slate-500)', marginTop: '4px' }}>
                      Slot Duration: {s.slot_duration_minutes} mins
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: PRACTICE INSIGHTS */}
      {activeTab === 'insights' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3>Practice Analytics & Volume</h3>
              <p style={{ color: 'var(--slate-500)', fontSize: '14px' }}>
                Rule-based SQL aggregation and deterministic clinic trends
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className={`btn-outline ${insightsRange === 'weekly' ? 'active' : ''}`}
                style={{
                  background: insightsRange === 'weekly' ? 'var(--primary-600)' : '#fff',
                  color: insightsRange === 'weekly' ? '#fff' : 'var(--slate-700)'
                }}
                onClick={() => setInsightsRange('weekly')}
              >
                Weekly
              </button>
              <button
                className={`btn-outline ${insightsRange === 'monthly' ? 'active' : ''}`}
                style={{
                  background: insightsRange === 'monthly' ? 'var(--primary-600)' : '#fff',
                  color: insightsRange === 'monthly' ? '#fff' : 'var(--slate-700)'
                }}
                onClick={() => setInsightsRange('monthly')}
              >
                Monthly
              </button>
            </div>
          </div>

          {/* Metrics Overview */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-icon blue"><Users size={24} /></div>
              <div>
                <div className="metric-value">{insightsData?.total_bookings || 0}</div>
                <div className="metric-label">Total Bookings</div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon rose"><AlertTriangle size={24} /></div>
              <div>
                <div className="metric-value">{insightsData?.total_cancellations || 0}</div>
                <div className="metric-label">Cancellations</div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon green"><Activity size={24} /></div>
              <div>
                <div className="metric-value">{insightsData?.new_patients_count || 0}</div>
                <div className="metric-label">New Patients</div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon amber"><Clock size={24} /></div>
              <div>
                <div className="metric-value" style={{ fontSize: '18px' }}>
                  {insightsData?.busiest_day || 'None'}
                </div>
                <div className="metric-label">Peak Demand Day</div>
              </div>
            </div>
          </div>

          {/* Rule-Based Practice Summary (No LLM) */}
          <div className="card" style={{ marginBottom: '24px', background: '#f0f9ff', borderColor: '#bae6fd' }}>
            <h4 style={{ color: '#0369a1', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} /> Deterministic Summary
            </h4>
            <p style={{ fontSize: '15px', color: '#0c4a6e', lineHeight: 1.6, margin: 0 }}>
              {insightsData?.summary_text}
            </p>
          </div>

          {/* Daily Activity Breakdown Bar */}
          <div className="card">
            <h4 style={{ marginBottom: '16px' }}>Daily Breakdown</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {insightsData?.daily_breakdown?.map((d, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '13px' }}>
                  <span style={{ width: '60px', fontWeight: 600, color: 'var(--slate-600)' }}>{d.date}</span>
                  <div style={{ flex: 1, height: '16px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                    <div style={{ width: `${Math.min(d.booked * 25, 100)}%`, background: 'var(--primary-600)', height: '100%' }} />
                    <div style={{ width: `${Math.min(d.cancelled * 25, 100)}%`, background: 'var(--accent-rose)', height: '100%' }} />
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--slate-600)' }}>
                    {d.booked} booked {d.cancelled > 0 ? `(${d.cancelled} cancelled)` : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: EMERGENCY BLOCK */}
      {activeTab === 'emergency' && (
        <div style={{ maxWidth: '680px', margin: '0 auto' }}>
          <div className="card" style={{ borderColor: '#fca5a5' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{ width: '42px', height: '42px', borderRadius: '50%', background: '#fee2e2', color: '#b91c1c', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ShieldAlert size={24} />
              </div>
              <div>
                <h3 style={{ color: '#991b1b', margin: 0 }}>Emergency Schedule Blocker</h3>
                <p style={{ color: '#7f1d1d', fontSize: '13px', margin: '2px 0 0 0' }}>
                  Immediately locks availability and automatically emails all scheduled patients with rescheduling guidance.
                </p>
              </div>
            </div>

            <form onSubmit={handleEmergencyBlock}>
              <div className="form-group">
                <label className="form-label">Select Date to Block</label>
                <input
                  type="date"
                  className="form-input"
                  required
                  min={new Date().toISOString().split('T')[0]}
                  value={blockDate}
                  onChange={(e) => setBlockDate(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Reason for Emergency Notice (Included in Patient Email)</label>
                <textarea
                  className="form-input"
                  rows={3}
                  value={blockReason}
                  onChange={(e) => setBlockReason(e.target.value)}
                  placeholder="Doctor emergency medical leave or hospital commitment..."
                />
              </div>

              <button type="submit" className="btn-danger" style={{ width: '100%', padding: '12px', justifyContent: 'center' }}>
                <ShieldAlert size={18} /> Confirm Emergency Block & Broadcast Email Alerts
              </button>
            </form>

            {blockResult && (
              <div style={{ marginTop: '24px', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--slate-200)' }}>
                <h4 style={{ color: '#0369a1', marginBottom: '8px' }}>Broadcast Summary</h4>
                <p style={{ fontSize: '13px', margin: '0 0 12px 0' }}>
                  Blocked Date: <strong>{blockResult.date}</strong> | Affected Consultations: <strong>{blockResult.affected_appointments_count}</strong>
                </p>
                {blockResult.notified_patients?.length > 0 && (
                  <ul style={{ paddingLeft: '20px', fontSize: '13px', color: 'var(--slate-700)' }}>
                    {blockResult.notified_patients.map((p, idx) => (
                      <li key={idx}>
                        {p.patient_name} ({p.patient_email}) — Time: {p.time_slot} [{p.booking_id}]
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
