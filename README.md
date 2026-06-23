# Event Ticket Booking System (Flask + MySQL)

A database-based Event Ticket Booking System developed as a university group project using Flask and MySQL.  
It allows customers to book events and organizers to manage events, venues, and bookings through a web interface.

---

## 🚀 Features

### 👤 Authentication
- Signup/Login with Customer and Organizer roles  
- Session-based authentication  
- Basic password validation  

### 🎯 Organizer
- Create, edit, and delete events  
- Add and manage venues  
- Seat capacity validation  
- Dashboard with event stats, bookings, and revenue  
- View all bookings  

### 🎟️ Customer
- Browse and search events  
- Book tickets with seat availability check  
- Payment options (Online / Cash on Event Day)  
- Cancel pending bookings  
- View booking history  

### 🔔 Notifications
- Booking and payment notifications stored in database  
- In-app notification system  

### ⏳ Booking System
- Pending bookings expire after 30 minutes  
- Automatic seat release on expiry  

---

## 🛠️ Tech Stack
- Backend: Python (Flask)  
- Database: MySQL  
- Frontend: HTML, CSS, Bootstrap (Jinja Templates)  

---

## 🗄️ Database Tables
- Users  
- Events  
- Venues  
- Bookings  
- Notifications  

---

## ⚙️ Setup Instructions

```bash
git clone <repo-url>
cd project
python -m venv venv
venv\Scripts\activate
pip install flask mysql-connector-python
