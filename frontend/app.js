/**
 * VoiceBookAI — Frontend Business Logic
 * Restored to original functional version for Glassmorphic UI.
 */

class VoiceBookUI {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.sessionId = this.getOrGenerateSessionId();

        // UI Elements
        this.recordBtn = document.getElementById('recordBtn');
        this.recordStatus = document.getElementById('recordStatus');
        this.chatMessages = document.getElementById('chatMessages');
        this.eventsList = document.getElementById('eventsList');
        this.bookingsList = document.getElementById('bookingsList');
        this.textInput = document.getElementById('textInput');
        this.sendTextBtn = document.getElementById('sendTextBtn');
        this.langSelect = document.getElementById('langSelect');
        this.audioPlayer = document.getElementById('audioPlayer');

        this.init();
    }

    getOrGenerateSessionId() {
        let sid = localStorage.getItem('sid');
        if (!sid) {
            sid = 'sess_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('sid', sid);
        }
        return sid;
    }

    init() {
        // Mode Tabs
        const voiceModeBtn = document.getElementById('voiceModeBtn');
        const textModeBtn = document.getElementById('textModeBtn');
        const voiceSection = document.getElementById('voiceMode');
        const textSection = document.getElementById('textMode');

        voiceModeBtn.onclick = () => {
            voiceModeBtn.classList.add('active');
            textModeBtn.classList.remove('active');
            voiceSection.classList.remove('hidden');
            textSection.classList.add('hidden');
        };

        textModeBtn.onclick = () => {
            textModeBtn.classList.add('active');
            voiceModeBtn.classList.remove('active');
            textSection.classList.remove('hidden');
            voiceSection.classList.add('hidden');
        };

        // Data Tabs
        const eventsTab = document.getElementById('eventsTab');
        const bookingsTab = document.getElementById('bookingsTab');
        const eventsContent = document.getElementById('eventsContent');
        const bookingsContent = document.getElementById('bookingsContent');

        eventsTab.onclick = () => {
            eventsTab.classList.add('active');
            bookingsTab.classList.remove('active');
            eventsContent.classList.add('active');
            bookingsContent.classList.remove('active');
        };

        bookingsTab.onclick = () => {
            bookingsTab.classList.add('active');
            eventsTab.classList.remove('active');
            bookingsContent.classList.add('active');
            eventsContent.classList.remove('active');
            this.fetchBookings();
        };

        // Microphone Button
        this.recordBtn.onclick = () => this.toggleRecording();

        // Text Input
        this.sendTextBtn.onclick = () => this.handleTextQuery();
        this.textInput.onkeypress = (e) => {
            if (e.key === 'Enter') this.handleTextQuery();
        };

        // Clear Chat
        document.getElementById('clearChat').onclick = () => {
            this.chatMessages.innerHTML = '';
            this.addBotMessage("Chat cleared. How can I help you?");
        };

        // Initial fetch
        this.fetchEvents();
    }

    async toggleRecording() {
        if (!this.isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.mediaRecorder = new MediaRecorder(stream);
                this.audioChunks = [];

                this.mediaRecorder.ondataavailable = (event) => {
                    this.audioChunks.push(event.data);
                };

                this.mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                    this.sendVoice(audioBlob);
                };

                this.mediaRecorder.start();
                this.isRecording = true;
                this.recordBtn.classList.add('recording');
                this.recordStatus.textContent = "Listening... Click again to stop";
            } catch (err) {
                console.error("Microphone access denied:", err);
                alert("Please allow microphone access to use voice booking.");
            }
        } else {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(t => t.stop());
            this.isRecording = false;
            this.recordBtn.classList.remove('recording');
            this.recordStatus.textContent = "Processing...";
        }
    }

    async sendVoice(blob) {
        const formData = new FormData();
        formData.append('audio', blob, 'voice.webm');
        formData.append('session_id', this.sessionId);

        try {
            const res = await fetch('/api/voice', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.transcript) {
                this.addUserMessage(data.transcript);
            }
            if (data.response_text) {
                this.addBotMessage(data.response_text);
            }
            if (data.events && data.events.length > 0) {
                this.renderEvents(data.events);
            }
            if (data.audio_url) {
                this.playVoice(data.audio_url);
            }
            if (data.booking) {
                this.fetchBookings();
            }

            this.recordStatus.textContent = "Click to start recording";
        } catch (err) {
            console.error("API error:", err);
            this.addBotMessage("Sorry, I encountered an error. Please try again.");
            this.recordStatus.textContent = "Error. Try again.";
        }
    }

    async handleTextQuery() {
        const text = this.textInput.value.trim();
        if (!text) return;

        this.textInput.value = '';
        this.addUserMessage(text);

        const params = new URLSearchParams({
            text: text,
            session_id: this.sessionId,
            language: this.langSelect.value
        });

        try {
            const res = await fetch('/api/text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: params
            });
            const data = await res.json();

            if (data.response_text) {
                this.addBotMessage(data.response_text);
            }
            if (data.events && data.events.length > 0) {
                this.renderEvents(data.events);
            }
            if (data.audio_url) {
                this.playVoice(data.audio_url);
            }
            if (data.booking) {
                this.fetchBookings();
            }
        } catch (err) {
            console.error("API error:", err);
            this.addBotMessage("Sorry, I couldn't reach the server.");
        }
    }

    addUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message user';
        msgDiv.innerHTML = `
            <div class="message-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <div class="message-content"><p>${text}</p></div>
        `;
        this.chatMessages.appendChild(msgDiv);
        this.scrollToBottom();
    }

    addBotMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message assistant';
        msgDiv.innerHTML = `
            <div class="message-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
            </div>
            <div class="message-content"><p>${text}</p></div>
        `;
        this.chatMessages.appendChild(msgDiv);
        this.scrollToBottom();
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    playVoice(url) {
        this.audioPlayer.src = url;
        this.audioPlayer.play();
    }

    async fetchEvents() {
        try {
            const res = await fetch('/api/events');
            const data = await res.json();
            this.renderEvents(data.events);
        } catch (err) {
            console.error("Fetch error:", err);
        }
    }

    renderEvents(events) {
        this.eventsList.innerHTML = '';
        if (events.length === 0) {
            this.eventsList.innerHTML = '<p class="empty-state">No matching events found.</p>';
            return;
        }

        events.forEach(event => {
            const card = document.createElement('div');
            card.className = 'event-card';
            card.innerHTML = `
                <div class="event-name">${event.name}</div>
                <div class="event-meta">
                    <div class="meta-item">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                        ${event.date}
                    </div>
                    <div class="meta-item">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                        ${event.time}
                    </div>
                    <div class="meta-item">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                        ${event.venue}
                    </div>
                </div>
                <div class="event-description">${event.description}</div>
                <div class="event-footer">
                    <span class="tag">${event.category}</span>
                    <span class="event-availability">
                        ${event.total_seats - event.booked_seats} seats left
                    </span>
                </div>
            `;
            this.eventsList.appendChild(card);
        });
    }

    async fetchBookings() {
        try {
            const res = await fetch('/api/bookings');
            const data = await res.json();
            this.renderBookings(data.bookings);
        } catch (err) {
            console.error("Fetch bookings error:", err);
        }
    }

    renderBookings(bookings) {
        this.bookingsList.innerHTML = '';
        if (!bookings || bookings.length === 0) {
            this.bookingsList.innerHTML = '<p class="empty-state">No bookings yet. Start chatting to book events!</p>';
            return;
        }

        bookings.forEach(b => {
            const div = document.createElement('div');
            div.className = 'booking-item';
            div.innerHTML = `
                <div class="booking-info">
                    <h4>${b.event_name || 'Event Booking'}</h4>
                    <p>${b.num_tickets} Ticket(s)</p>
                </div>
                <div class="ref-code">${b.reference_code}</div>
            `;
            this.bookingsList.appendChild(div);
        });
    }
}

// Start App
const app = new VoiceBookUI();
