"""SQLite database setup, seeding, and query functions."""

import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

from backend.models import Event, Booking

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "events.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the DB directory if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            venue TEXT NOT NULL,
            total_seats INTEGER NOT NULL,
            booked_seats INTEGER NOT NULL DEFAULT 0,
            description TEXT NOT NULL,
            description_hi TEXT DEFAULT '',
            description_te TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_code TEXT UNIQUE NOT NULL,
            event_id INTEGER NOT NULL,
            num_tickets INTEGER NOT NULL,
            user_language TEXT DEFAULT 'en',
            booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_events():
    """Seed the database with 15 sample events if empty."""
    conn = get_connection()
    cursor = conn.cursor()

    count = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if count > 0:
        conn.close()
        return

    events = [
        # --- Music ---
        {
            "name": "Classical Carnatic Concert",
            "category": "Music",
            "date": "2026-03-07",
            "time": "18:00",
            "venue": "Ravindra Bharathi, Hyderabad",
            "total_seats": 200,
            "booked_seats": 200,  # FULLY BOOKED — for testing recommendations
            "description": "An evening of soulful Carnatic music featuring renowned artists.",
            "description_hi": "प्रसिद्ध कलाकारों के साथ कर्नाटक संगीत की एक भावपूर्ण शाम।",
            "description_te": "ప్రముఖ కళాకారులతో కర్ణాటక సంగీతం యొక్క ఒక హృదయస్పర్శి సాయంత్రం."
        },
        {
            "name": "Bollywood Night Live",
            "category": "Music",
            "date": "2026-03-08",
            "time": "19:30",
            "venue": "Shilpakala Vedika, Hyderabad",
            "total_seats": 500,
            "booked_seats": 120,
            "description": "Dance to the biggest Bollywood hits performed live by a full band.",
            "description_hi": "एक पूरे बैंड द्वारा लाइव प्रदर्शित सबसे बड़े बॉलीवुड हिट्स पर नाचें।",
            "description_te": "ఒక పూర్తి బ్యాండ్ ద్వారా ప్రత్యక్షంగా ప్రదర్శించబడిన అతిపెద్ద బాలీవుడ్ హిట్‌లకు నాట్యం చేయండి."
        },
        {
            "name": "Indie Music Festival",
            "category": "Music",
            "date": "2026-03-09",
            "time": "16:00",
            "venue": "People's Plaza, Hyderabad",
            "total_seats": 300,
            "booked_seats": 50,
            "description": "A celebration of independent musicians from across India.",
            "description_hi": "भारत भर के स्वतंत्र संगीतकारों का उत्सव।",
            "description_te": "భారతదేశం అంతటా నుండి స్వతంత్ర సంగీతకారుల ఉత్సవం."
        },
        # --- Dance ---
        {
            "name": "Kuchipudi Dance Performance",
            "category": "Dance",
            "date": "2026-03-07",
            "time": "17:00",
            "venue": "Tyagaraja Gana Sabha, Hyderabad",
            "total_seats": 150,
            "booked_seats": 150,  # FULLY BOOKED
            "description": "A mesmerizing Kuchipudi recital by award-winning dancers.",
            "description_hi": "पुरस्कार विजेता नर्तकों द्वारा एक मंत्रमुग्ध कर देने वाली कुचिपुड़ी प्रस्तुति।",
            "description_te": "అవార్డు విజేత నర్తకులచే ఒక మంత్రముగ్ధ కుచిపుడి ప్రదర్శన."
        },
        {
            "name": "Contemporary Dance Workshop",
            "category": "Dance",
            "date": "2026-03-08",
            "time": "10:00",
            "venue": "Lamakaan, Hyderabad",
            "total_seats": 30,
            "booked_seats": 10,
            "description": "Learn contemporary dance techniques in this hands-on workshop.",
            "description_hi": "इस व्यावहारिक कार्यशाला में समकालीन नृत्य तकनीकें सीखें।",
            "description_te": "ఈ ప్రాక్టికల్ వర్క్‌షాప్‌లో సమకాలీన నృత్య పద్ధతులను నేర్చుకోండి."
        },
        # --- Photography ---
        {
            "name": "Street Photography Masterclass",
            "category": "Photography",
            "date": "2026-03-08",
            "time": "08:00",
            "venue": "Charminar Area, Hyderabad",
            "total_seats": 20,
            "booked_seats": 18,
            "description": "Capture the vibrant streets of Hyderabad with a professional photographer.",
            "description_hi": "एक पेशेवर फोटोग्राफर के साथ हैदराबाद की जीवंत सड़कों को कैप्चर करें।",
            "description_te": "ఒక ప్రొఫెషనల్ ఫోటోగ్రాఫర్‌తో హైదరాబాద్ యొక్క జీవంతమైన వీధులను క్యాప్చర్ చేయండి."
        },
        {
            "name": "Photography Workshop — Portraits",
            "category": "Photography",
            "date": "2026-03-09",
            "time": "14:00",
            "venue": "Durgam Cheruvu, Hyderabad",
            "total_seats": 25,
            "booked_seats": 5,
            "description": "Master portrait photography with natural light techniques.",
            "description_hi": "प्राकृतिक प्रकाश तकनीकों के साथ पोर्ट्रेट फोटोग्राफी में महारत हासिल करें।",
            "description_te": "సహజ కాంతి పద్ధతులతో పోర్ట్రెయిట్ ఫోటోగ్రఫీలో నైపుణ్యం పొందండి."
        },
        # --- Comedy ---
        {
            "name": "Stand-up Comedy Night",
            "category": "Comedy",
            "date": "2026-03-07",
            "time": "20:00",
            "venue": "The Moonshine Project, Hyderabad",
            "total_seats": 80,
            "booked_seats": 75,
            "description": "Laugh out loud with top comics performing their best sets.",
            "description_hi": "शीर्ष कॉमेडियनों के बेहतरीन सेट्स के साथ जोर-जोर से हंसें।",
            "description_te": "టాప్ కమెడియన్ల బెస్ట్ సెట్స్‌తో బాగా నవ్వండి."
        },
        {
            "name": "Improv Comedy Show",
            "category": "Comedy",
            "date": "2026-03-09",
            "time": "19:00",
            "venue": "Aalankrita Resort, Hyderabad",
            "total_seats": 60,
            "booked_seats": 20,
            "description": "Unscripted, hilarious improv comedy — every show is unique!",
            "description_hi": "अनस्क्रिप्टेड, हंसाने वाली इम्प्रोव कॉमेडी — हर शो अनोखा है!",
            "description_te": "స్క్రిప్ట్ లేని, నవ్వించే ఇంప్రూవ్ కామెడీ — ప్రతి షో ప్రత్యేకం!"
        },
        # --- Art ---
        {
            "name": "Watercolor Painting Workshop",
            "category": "Art",
            "date": "2026-03-08",
            "time": "11:00",
            "venue": "State Art Gallery, Hyderabad",
            "total_seats": 25,
            "booked_seats": 8,
            "description": "Explore watercolor techniques from beginner to intermediate level.",
            "description_hi": "शुरुआती से मध्यवर्ती स्तर तक वॉटरकलर तकनीकें सीखें।",
            "description_te": "ప్రారంభ స్థాయి నుండి మధ్యస్థ స్థాయి వరకు వాటర్‌కలర్ పద్ధతులను అన్వేషించండి."
        },
        # --- Tech ---
        {
            "name": "AI & Machine Learning Talk",
            "category": "Tech",
            "date": "2026-03-09",
            "time": "10:00",
            "venue": "T-Hub, Hyderabad",
            "total_seats": 100,
            "booked_seats": 45,
            "description": "Industry experts discuss the future of AI and practical ML applications.",
            "description_hi": "उद्योग विशेषज्ञ AI के भविष्य और व्यावहारिक ML अनुप्रयोगों पर चर्चा करते हैं।",
            "description_te": "పరిశ్రమ నిపుణులు AI భవిష్యత్తు మరియు ఆచరణాత్మక ML అప్లికేషన్ల గురించి చర్చిస్తారు."
        },
        {
            "name": "Web Development Bootcamp",
            "category": "Tech",
            "date": "2026-03-10",
            "time": "09:00",
            "venue": "IIIT Hyderabad",
            "total_seats": 50,
            "booked_seats": 50,  # FULLY BOOKED
            "description": "Full-day hands-on bootcamp covering React, Node.js, and deployment.",
            "description_hi": "React, Node.js और डिप्लॉयमेंट पर पूरे दिन का हैंड्स-ऑन बूटकैम्प।",
            "description_te": "React, Node.js మరియు deployment పై పూర్తి రోజు హ్యాండ్స్-ఆన్ బూట్‌క్యాంప్."
        },
        # --- Cooking ---
        {
            "name": "Hyderabadi Biryani Cooking Class",
            "category": "Cooking",
            "date": "2026-03-08",
            "time": "12:00",
            "venue": "Taj Falaknuma Palace, Hyderabad",
            "total_seats": 15,
            "booked_seats": 12,
            "description": "Learn the authentic Hyderabadi Dum Biryani recipe from a master chef.",
            "description_hi": "एक मास्टर शेफ से प्रामाणिक हैदराबादी दम बिरयानी रेसिपी सीखें।",
            "description_te": "ఒక మాస్టర్ చెఫ్ నుండి ఆథెంటిక్ హైదరాబాదీ దమ్ బిర్యానీ రెసిపీ నేర్చుకోండి."
        },
        # --- Yoga ---
        {
            "name": "Sunrise Yoga Session",
            "category": "Yoga",
            "date": "2026-03-09",
            "time": "06:00",
            "venue": "KBR National Park, Hyderabad",
            "total_seats": 40,
            "booked_seats": 15,
            "description": "Start your Sunday with a rejuvenating outdoor yoga session.",
            "description_hi": "एक ताज़गी भरे आउटडोर योग सत्र के साथ अपने रविवार की शुरुआत करें।",
            "description_te": "ఒక ఉత్తేజకరమైన అవుట్‌డోర్ యోగా సెషన్‌తో మీ ఆదివారాన్ని ప్రారంభించండి."
        },
        {
            "name": "Evening Meditation & Yoga",
            "category": "Yoga",
            "date": "2026-03-10",
            "time": "17:30",
            "venue": "Necklace Road Park, Hyderabad",
            "total_seats": 35,
            "booked_seats": 10,
            "description": "Wind down with an evening session combining yoga and guided meditation.",
            "description_hi": "योग और निर्देशित ध्यान को मिलाकर शाम के सत्र के साथ आराम करें।",
            "description_te": "యోగా మరియు గైడెడ్ మెడిటేషన్‌ను కలిపి సాయంత్రం సెషన్‌తో విశ్రాంతి తీసుకోండి."
        },
    ]

    cursor = conn.cursor()
    for event in events:
        cursor.execute("""
            INSERT INTO events (name, category, date, time, venue, total_seats, booked_seats,
                                description, description_hi, description_te)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["name"], event["category"], event["date"], event["time"],
            event["venue"], event["total_seats"], event["booked_seats"],
            event["description"], event["description_hi"], event["description_te"]
        ))

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(events)} events into {DB_PATH}")


# ── Query Functions ──────────────────────────────────────────────

def get_all_events() -> list[Event]:
    """Get all events."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM events ORDER BY date, time").fetchall()
    conn.close()
    return [Event(**dict(r)) for r in rows]


def get_event_by_id(event_id: int) -> Optional[Event]:
    """Get a single event by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return Event(**dict(row)) if row else None


def search_events(
    name: Optional[str] = None,
    category: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
) -> list[Event]:
    """Search events by name, category, date, or time. Uses LIKE for partial matching on name."""
    conn = get_connection()
    query = "SELECT * FROM events WHERE 1=1"
    params: list = []

    if name:
        query += " AND LOWER(name) LIKE ?"
        params.append(f"%{name.lower()}%")
    if category:
        query += " AND LOWER(category) LIKE ?"
        params.append(f"%{category.lower()}%")
    if date:
        query += " AND date = ?"
        params.append(date)
    if time:
        query += " AND time = ?"
        params.append(time)

    query += " ORDER BY date, time"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [Event(**dict(r)) for r in rows]


def check_availability(event_id: int, num_tickets: int = 1) -> tuple[bool, int]:
    """Check if an event has enough seats. Returns (is_available, available_seats)."""
    event = get_event_by_id(event_id)
    if not event:
        return False, 0
    available = event.available_seats
    return available >= num_tickets, available


def update_booked_seats(event_id: int, additional: int) -> bool:
    """Atomically increment booked_seats for an event. Returns True if successful."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE events
        SET booked_seats = booked_seats + ?
        WHERE id = ? AND (booked_seats + ?) <= total_seats
    """, (additional, event_id, additional))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def save_booking(booking: Booking) -> Booking:
    """Save a booking record to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bookings (reference_code, event_id, num_tickets, user_language)
        VALUES (?, ?, ?, ?)
    """, (booking.reference_code, booking.event_id, booking.num_tickets, booking.user_language))
    booking.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return booking


def get_all_bookings() -> list[dict]:
    """Get all bookings with event names."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT b.*, e.name as event_name 
        FROM bookings b
        JOIN events e ON b.event_id = e.id
        ORDER BY b.booked_at DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Initialization ───────────────────────────────────────────────

def setup_database():
    """Initialize DB and seed events."""
    init_db()
    seed_events()
