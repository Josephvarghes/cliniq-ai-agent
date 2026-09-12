const API_BASE_URL = 'http://localhost:8000';

export async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem('cliniq_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = data?.detail || `Error ${response.status}: Request failed`;
    throw new Error(errorMsg);
  }

  return data;
}

export const api = {
  // Auth
  patientSignup: (payload) => apiRequest('/auth/patient/signup', { method: 'POST', body: JSON.stringify(payload) }),
  patientLogin: (payload) => apiRequest('/auth/patient/login', { method: 'POST', body: JSON.stringify(payload) }),
  doctorLogin: (payload) => apiRequest('/auth/doctor/login', { method: 'POST', body: JSON.stringify(payload) }),

  // Chatbot
  sendChatMessage: (payload) => apiRequest('/chatbot/message', { method: 'POST', body: JSON.stringify(payload) }),
  getAvailability: (dateStr) => apiRequest(`/chatbot/availability?date=${dateStr}`),

  // Patient Bookings
  getPatientBookings: (patientId, statusFilter) => {
    const query = statusFilter ? `?status_filter=${statusFilter}` : '';
    return apiRequest(`/patients/${patientId}/bookings${query}`);
  },

  // Appointments
  bookAppointment: (payload) => apiRequest('/appointments/book', { method: 'POST', body: JSON.stringify(payload) }),
  cancelAppointment: (id) => apiRequest(`/appointments/${id}/cancel`, { method: 'POST' }),
  rescheduleAppointment: (id, payload) => apiRequest(`/appointments/${id}/reschedule`, { method: 'POST', body: JSON.stringify(payload) }),

  // Doctor CRM
  getDoctorDashboard: (doctorId) => apiRequest(`/doctors/${doctorId}/dashboard`),
  getDoctorSchedule: (doctorId) => apiRequest(`/doctors/${doctorId}/schedule`),
  createDoctorSchedule: (doctorId, payload) => apiRequest(`/doctors/${doctorId}/schedule`, { method: 'POST', body: JSON.stringify(payload) }),
  emergencyBlockSchedule: (doctorId, payload) => apiRequest(`/doctors/${doctorId}/schedule/block`, { method: 'POST', body: JSON.stringify(payload) }),
  getDoctorInsights: (doctorId, range = 'monthly') => apiRequest(`/doctors/${doctorId}/insights?range=${range}`),
  getDoctorEnquiries: (doctorId) => apiRequest(`/doctors/${doctorId}/enquiries`)
};
