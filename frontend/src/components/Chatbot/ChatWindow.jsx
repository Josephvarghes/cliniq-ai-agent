import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { Send, RotateCcw, Bot, User, Calendar as CalendarIcon, Clock, CheckCircle } from 'lucide-react';

export default function ChatWindow({ onNavigateToBookings }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [quickReplies, setQuickReplies] = useState([]);
  const [actionType, setActionType] = useState('buttons');
  const [sessionData, setSessionData] = useState({ state: 'INIT' });
  const [customDate, setCustomDate] = useState('');

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Initial welcome message
  useEffect(() => {
    startNewConversation();
  }, []);

  const startNewConversation = async () => {
    setLoading(true);
    try {
      const res = await api.sendChatMessage({ action_value: 'RESET' });
      setMessages([
        {
          sender: 'bot',
          text: res.reply_text,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
      setQuickReplies(res.quick_replies || []);
      setActionType(res.action_type || 'buttons');
      setSessionData(res.session_data || { state: 'INIT' });
    } catch (err) {
      console.error(err);
      setMessages([
        {
          sender: 'bot',
          text: 'Welcome! I am your clinical booking assistant. How can I help you today?',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (textToSend = null, actionValue = null) => {
    const text = textToSend !== null ? textToSend : inputText.trim();
    if (!text && !actionValue) return;

    // Check special redirect action
    if (actionValue === 'REDIRECT_BOOKINGS') {
      onNavigateToBookings?.();
      return;
    }

    const newMsgs = [...messages];
    if (text) {
      newMsgs.push({
        sender: 'user',
        text: text,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      });
      setMessages(newMsgs);
    }

    setInputText('');
    setLoading(true);

    try {
      const res = await api.sendChatMessage({
        message: text || undefined,
        action_value: actionValue || undefined,
        payload: sessionData
      });

      setMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: res.reply_text,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);

      setQuickReplies(res.quick_replies || []);
      setActionType(res.action_type || 'buttons');
      setSessionData(res.session_data || { state: 'INIT' });
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: `⚠️ Error: ${err.message || 'Failed to process request.'}`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleChipClick = (chip) => {
    if (chip.value === 'REDIRECT_BOOKINGS') {
      onNavigateToBookings?.();
      return;
    }
    handleSend(chip.label, chip.value);
  };

  const handleDateSubmit = (e) => {
    e.preventDefault();
    if (customDate) {
      handleSend(`Date: ${customDate}`, `DATE_${customDate}`);
      setCustomDate('');
    }
  };

  // Helper to format text with bolding and icons
  const renderFormattedText = (txt) => {
    const parts = txt.split('\n');
    return parts.map((line, idx) => {
      // Format bold markdown **bold**
      const formattedLine = line.split(/(\*\*.*?\*\*|`.*?`)/g).map((chunk, cIdx) => {
        if (chunk.startsWith('**') && chunk.endsWith('**')) {
          return <strong key={cIdx}>{chunk.slice(2, -2)}</strong>;
        }
        if (chunk.startsWith('`') && chunk.endsWith('`')) {
          return (
            <code
              key={cIdx}
              style={{
                background: '#e2e8f0',
                padding: '2px 6px',
                borderRadius: '4px',
                color: '#0369a1',
                fontWeight: '700'
              }}
            >
              {chunk.slice(1, -1)}
            </code>
          );
        }
        return chunk;
      });

      return (
        <React.Fragment key={idx}>
          {formattedLine}
          {idx < parts.length - 1 && <br />}
        </React.Fragment>
      );
    });
  };

  return (
    <div className="chatbot-wrapper">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-doctor-info">
          <div className="doctor-avatar-circle">🩺</div>
          <div>
            <h3 style={{ margin: 0, fontSize: '16px', color: '#fff' }}>Cliniq Assistant</h3>
            <p style={{ margin: '2px 0 0 0', fontSize: '12px', opacity: 0.9 }}>
              Dr. Joseph Varghese's Practice • 🟢 Live Online
            </p>
          </div>
        </div>
        <button
          className="btn-outline"
          style={{ padding: '6px 12px', fontSize: '12px', background: 'rgba(255,255,255,0.15)', color: '#fff', borderColor: 'transparent' }}
          onClick={startNewConversation}
          title="Restart Conversation"
        >
          <RotateCcw size={14} /> Restart
        </button>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((m, idx) => (
          <div key={idx} className={`message-row ${m.sender}`}>
            <div className="message-avatar">
              {m.sender === 'bot' ? <Bot size={18} /> : <User size={18} />}
            </div>
            <div className="message-bubble">
              {renderFormattedText(m.text)}
              <div style={{ fontSize: '10px', opacity: 0.7, marginTop: '4px', textAlign: 'right' }}>
                {m.time}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="message-row bot">
            <div className="message-avatar"><Bot size={18} /></div>
            <div className="message-bubble" style={{ color: 'var(--slate-500)', fontStyle: 'italic' }}>
              Checking clinic calendar...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Interactive Quick Reply Tray */}
      {quickReplies.length > 0 && !loading && (
        <div className="quick-replies-tray">
          {quickReplies.map((chip, idx) => {
            let extraClass = '';
            if (chip.value.includes('CONFIRM') || chip.value.includes('YES')) extraClass = 'confirm-yes';
            if (chip.value.includes('CANCEL') || chip.value.includes('RESET')) extraClass = 'confirm-no';

            return (
              <button
                key={idx}
                className={`chip-btn ${extraClass}`}
                onClick={() => handleChipClick(chip)}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      )}

      {/* Inline Date Picker Widget if action_type == 'date_picker' */}
      {actionType === 'date_picker' && !loading && (
        <form onSubmit={handleDateSubmit} style={{ padding: '10px 20px', background: '#f1f5f9', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <CalendarIcon size={18} style={{ color: 'var(--primary-600)' }} />
          <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--slate-700)' }}>Pick Date:</span>
          <input
            type="date"
            className="form-input"
            style={{ padding: '6px 12px', width: 'auto', flex: 1 }}
            value={customDate}
            min={new Date().toISOString().split('T')[0]}
            onChange={(e) => setCustomDate(e.target.value)}
          />
          <button type="submit" className="btn-primary" style={{ padding: '7px 14px' }}>
            Check Slots
          </button>
        </form>
      )}

      {/* Input Bar */}
      <form
        className="chat-input-bar"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <input
          type="text"
          className="chat-input"
          placeholder="Type 'book appointment', 'reschedule', or ask an enquiry..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="btn-primary btn-pill"
          style={{ width: '42px', height: '42px', padding: 0 }}
          disabled={loading || !inputText.trim()}
          title="Send message"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
