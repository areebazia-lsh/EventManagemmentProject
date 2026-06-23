from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import hashlib
from datetime import datetime
import re


app = Flask(__name__)
app.secret_key = "eventbook_2025_secret"


# Password: min 8 chars, at least 1 special (non-letter/digit) character
PASSWORD_PATTERN = re.compile(r'^(?=.*[^A-Za-z0-9]).{8,}$')



def get_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="Win678@",
            database="EventManagementt",
        )
    except:
        return None



def simple_hash(password):
    return hashlib.md5(password.encode()).hexdigest()



# ---------- CONTEXT PROCESSOR: NAVBAR VISIBILITY ----------


@app.context_processor
def inject_nav_visibility():
    """
    in_base_navbar: True -> navbar show
    False -> navbar hide (home, customer/organizer login, signup)
    """
    hide_paths = {"/", "/login/customer", "/login/organizer", "/signup"}
    show_nav = request.path not in hide_paths
    return {"show_navbar": show_nav}



# ========== NOTIFICATIONS HELPERS ==========


def create_notification(user_id, title, message):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO Notifications (user_id, title, message, type) 
                VALUES (%s, %s, %s, 'system')
                """,
                (user_id, title, message),
            )
            conn.commit()
        except:
            pass
        finally:
            cur.close()
            conn.close()



def notify_organizer_booking(event_id, customer_name, qty, total):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT organizer_id FROM Events WHERE event_id = %s", (event_id,)
            )
            result = cur.fetchone()
            if result:
                organizer_id = result[0]
                msg = f"{customer_name} booked {qty} tickets for Rs{total}"
                create_notification(organizer_id, "🔔 New Booking!", msg)
        except:
            pass
        finally:
            cur.close()
            conn.close()



def get_notifications(user_id):
    conn = get_connection()
    notifications = []
    if conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT notification_id, title, message, created_at, is_read 
                FROM Notifications 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 10
                """,
                (user_id,),
            )
            notifications = cur.fetchall()
        except:
            pass
        finally:
            cur.close()
            conn.close()
    return notifications



def check_expired_bookings():
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT booking_id, quantity, event_id 
                FROM Bookings 
                WHERE status = 'Pending' 
                AND TIMESTAMPDIFF(MINUTE, booking_date, NOW()) > 30
                """
            )
            expired = cur.fetchall()
            for booking in expired:
                cur.execute(
                    "UPDATE Events SET booked_seats = booked_seats - %s WHERE event_id = %s",
                    (booking[1], booking[2]),
                )
                cur.execute(
                    "DELETE FROM Bookings WHERE booking_id = %s", (booking[0],)
                )
            conn.commit()
        except:
            pass
        finally:
            cur.close()
            conn.close()



# ========== HOME & LOGOUT ==========


@app.route("/")
def home():
    return render_template("home.html")



@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!")
    return redirect("/")



# ========== LOGIN ==========


@app.route("/login/customer", methods=["GET", "POST"])
def login_customer():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = simple_hash(request.form["password"])
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT user_id, name, role 
                FROM Users 
                WHERE email=%s AND password=%s AND role='customer'
                """,
                (email, password),
            )
            user = cur.fetchone()
            print("LOGIN CUSTOMER USER:", user)
            cur.close()
            conn.close()

            if user:
                session["user_id"] = user[0]
                session["name"] = user[1]
                session["role"] = user[2]
                return redirect("/customer/dashboard")
            else:
                flash("Invalid customer credentials!")
    return render_template("login_customer.html")



@app.route("/login/organizer", methods=["GET", "POST"])
def login_organizer():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = simple_hash(request.form["password"])
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT user_id, name, role 
                FROM Users 
                WHERE email=%s AND password=%s AND role='organizer'
                """,
                (email, password),
            )
            user = cur.fetchone()
            print("LOGIN ORGANIZER USER:", user)
            cur.close()
            conn.close()

            if user:
                session["user_id"] = user[0]
                session["name"] = user[1]
                session["role"] = user[2]
                return redirect("/organizer/dashboard")
            else:
                flash("Invalid organizer credentials!")
    return render_template("login_organizer.html")



# ========== SIGNUP ==========


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        raw_password = request.form["password"]

        # Password: min 8 chars + 1 special char
        if not PASSWORD_PATTERN.match(raw_password):
            flash("Password must be at least 8 characters and include 1 special character.")
            return redirect("/signup")

        password = simple_hash(raw_password)
        role = request.form.get("role", "customer")

        conn = get_connection()
        if conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT user_id FROM Users WHERE email=%s", (email,))
                if cur.fetchone():
                    flash("Email already registered. Please login.")
                    return redirect("/login/customer")

                cur.execute(
                    """
                    INSERT INTO Users (name, email, password, role)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (name, email, password, role),
                )
                conn.commit()
                flash("Account created! Please login.")
                if role == "organizer":
                    return redirect("/login/organizer")
                return redirect("/login/customer")
            finally:
                cur.close()
                conn.close()
    return render_template("signup.html")



# ========== CUSTOMER ROUTES ==========


@app.route("/customer/dashboard")
def customer_dashboard():
    if session.get("role") != "customer":
        return redirect("/login/customer")
    conn = get_connection()
    events = []
    notifications = get_notifications(session["user_id"])
    search_query = request.args.get("search", "").strip()
    if conn:
        cur = conn.cursor()
        try:
            if search_query:
                cur.execute(
                    """
                    SELECT e.event_id, e.event_name, e.event_date, e.price, v.venue_name, 
                           e.total_seats, e.booked_seats, e.event_time
                    FROM Events e 
                    JOIN Venues v ON e.venue_id = v.venue_id 
                    WHERE e.event_name LIKE %s OR v.venue_name LIKE %s
                    """,
                    (f"%{search_query}%", f"%{search_query}%"),
                )
            else:
                cur.execute(
                    """
                    SELECT e.event_id, e.event_name, e.event_date, e.price, v.venue_name, 
                           e.total_seats, e.booked_seats, e.event_time
                    FROM Events e 
                    JOIN Venues v ON e.venue_id = v.venue_id 
                    WHERE e.event_date >= CURDATE()
                    """
                )
            events = cur.fetchall()
        finally:
            cur.close()
            conn.close()
    return render_template(
        "customer_dashboard.html",
        events=events,
        name=session.get("name"),
        notifications=notifications,
    )



@app.route("/customer/payments")
def customer_payments():
    if session.get("role") != "customer":
        return redirect("/login/customer")

    check_expired_bookings()
    conn = get_connection()
    payments = []
    notifications = get_notifications(session["user_id"])

    status_filter = request.args.get("status", "").strip()
    when_filter = request.args.get("when", "").strip()
    search_query = request.args.get("q", "").strip()

    if conn:
        cur = conn.cursor()
        try:
            query = """
                SELECT b.booking_id, e.event_name, e.event_date, b.quantity, 
                       b.total_amount, b.status, b.booking_date
                FROM Bookings b 
                JOIN Events e ON b.event_id = e.event_id 
                WHERE b.customer_id = %s
            """
            params = [session["user_id"]]

            if status_filter in ["Pending", "Confirmed"]:
                query += " AND b.status = %s"
                params.append(status_filter)

            if when_filter == "upcoming":
                query += " AND e.event_date >= CURDATE()"
            elif when_filter == "past":
                query += " AND e.event_date < CURDATE()"

            if search_query:
                query += " AND e.event_name LIKE %s"
                params.append(f"%{search_query}%")

            query += " ORDER BY b.booking_date DESC"

            cur.execute(query, tuple(params))
            payments = cur.fetchall()
        finally:
            cur.close()
            conn.close()

    return render_template(
        "customer_payments.html",
        payments=payments,
        notifications=notifications,
        status_filter=status_filter,
        when_filter=when_filter,
        search_query=search_query,
    )



@app.route("/book/<int:event_id>", methods=["GET", "POST"])
def book_event(event_id):
    if session.get("role") != "customer":
        return redirect("/login/customer")
    conn = get_connection()
    if not conn:
        return redirect("/customer/dashboard")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.event_id, e.event_name, e.event_date, e.event_time, e.price, 
               v.venue_name, e.total_seats, e.booked_seats
        FROM Events e 
        JOIN Venues v ON e.venue_id = v.venue_id 
        WHERE e.event_id = %s
        """,
        (event_id,),
    )
    event = cur.fetchone()
    if not event:
        flash("Event not found!")
        cur.close()
        conn.close()
        return redirect("/customer/dashboard")

    available = event[6] - event[7]
    notifications = get_notifications(session["user_id"])

    if request.method == "POST":
        qty = int(request.form["quantity"])
        customer_name = session["name"]

        if qty > available or qty <= 0:
            flash(f"Only {available} seats available!")
        else:
            total = qty * event[4]
            cur.execute(
                """
                INSERT INTO Bookings 
                    (customer_id, event_id, quantity, total_amount, status, booking_date)
                VALUES (%s,%s,%s,%s,'Pending',NOW())
                """,
                (session["user_id"], event_id, qty, total),
            )
            cur.execute(
                "UPDATE Events SET booked_seats = booked_seats + %s WHERE event_id = %s",
                (qty, event_id),
            )
            conn.commit()

            create_notification(
                session["user_id"],
                "Booking Pending",
                f"{qty} tickets for {event[1]} - Pay within 30min! Total: Rs{total}",
            )
            notify_organizer_booking(event_id, customer_name, qty, total)

            flash(f"✅ Booked {qty} tickets! Pay within 30 minutes.")
            cur.close()
            conn.close()
            return redirect("/customer/payments")

    cur.close()
    conn.close()
    return render_template(
        "book_event.html",
        event=event,
        available=available,
        notifications=notifications,
    )



@app.route("/pay/<int:booking_id>", methods=["POST"])
def pay_booking(booking_id):
    if session.get("role") != "customer":
        return redirect("/customer/payments")
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            payment_method = request.form.get("payment_method", "Online")

            cur.execute("""
                SELECT b.quantity, b.event_id, b.status, 
                       TIMESTAMPDIFF(MINUTE, b.booking_date, NOW()) as minutes
                FROM Bookings b 
                WHERE b.booking_id = %s AND b.customer_id = %s
            """, (booking_id, session["user_id"]))
            booking = cur.fetchone()

            if booking and booking[2] == 'Pending' and booking[3] <= 30:
                if payment_method == "Cash":
                    # Cash on event day -> keep Pending
                    create_notification(
                        session["user_id"],
                        "Cash Payment Selected",
                        "You chose Cash on Event Day. Please pay at the venue to confirm."
                    )
                    flash("Cash on Event Day selected. Pay at venue to confirm your booking.")
                else:
                    # Online/card etc. -> confirm now
                    cur.execute(
                        "UPDATE Bookings SET status = 'Confirmed' WHERE booking_id = %s",
                        (booking_id,)
                    )
                    conn.commit()

                    create_notification(
                        session["user_id"],
                        "Payment Confirmed",
                        f"Your booking is now confirmed via {payment_method}!"
                    )
                    flash(f"✅ Payment Confirmed via {payment_method}! Ticket secured.")
            else:
                flash("❌ Too late! Booking expired or already confirmed.")
        finally:
            cur.close()
            conn.close()
    return redirect("/customer/payments")



@app.route("/cancel/<int:booking_id>")
def cancel_booking(booking_id):
    if session.get("role") != "customer":
        return redirect("/customer/payments")
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT quantity, event_id, status 
                FROM Bookings 
                WHERE booking_id = %s AND customer_id = %s
                """,
                (booking_id, session["user_id"]),
            )
            booking = cur.fetchone()
            if booking and booking[2] == "Pending":
                cur.execute(
                    "UPDATE Events SET booked_seats = booked_seats - %s WHERE event_id = %s",
                    (booking[0], booking[1]),
                )
                cur.execute(
                    "DELETE FROM Bookings WHERE booking_id = %s", (booking_id,)
                )
                conn.commit()
                flash("✅ Booking cancelled!")
            else:
                flash("Cannot cancel confirmed booking!")
        finally:
            cur.close()
            conn.close()
    return redirect("/customer/payments")



# ========== ORGANIZER ROUTES ==========


@app.route("/organizer/dashboard")
def organizer_dashboard():
    if session.get("role") != "organizer":
        return redirect("/login/organizer")
    conn = get_connection()
    events = []
    venues = []
    notifications = get_notifications(session["user_id"])
    search_query = request.args.get("search", "").strip()

    total_events = 0
    total_tickets_sold = 0
    total_revenue = 0

    if conn:
        cur = conn.cursor()
        try:
            if search_query:
                cur.execute("""
                    SELECT e.event_id, e.event_name, e.event_date, v.venue_name, 
                           e.total_seats, e.booked_seats, e.price
                    FROM Events e 
                    JOIN Venues v ON e.venue_id = v.venue_id 
                    WHERE e.organizer_id = %s 
                      AND (e.event_name LIKE %s OR v.venue_name LIKE %s)
                """, (session["user_id"], f"%{search_query}%", f"%{search_query}%"))
            else:
                cur.execute("""
                    SELECT e.event_id, e.event_name, e.event_date, v.venue_name, 
                           e.total_seats, e.booked_seats, e.price
                    FROM Events e 
                    JOIN Venues v ON e.venue_id = v.venue_id 
                    WHERE e.organizer_id = %s
                """, (session["user_id"],))
            events = cur.fetchall()

            cur.execute("""
                SELECT venue_id, venue_name, city, capacity 
                FROM Venues 
                ORDER BY venue_name
            """)
            venues = cur.fetchall()

            cur.execute("""
                SELECT COUNT(*) 
                FROM Events 
                WHERE organizer_id = %s
            """, (session["user_id"],))
            total_events = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT COALESCE(SUM(b.quantity), 0)
                FROM Bookings b
                JOIN Events e ON b.event_id = e.event_id
                WHERE e.organizer_id = %s AND b.status = 'Confirmed'
            """, (session["user_id"],))
            total_tickets_sold = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT COALESCE(SUM(b.total_amount), 0)
                FROM Bookings b
                JOIN Events e ON b.event_id = e.event_id
                WHERE e.organizer_id = %s AND b.status = 'Confirmed'
            """, (session["user_id"],))
            total_revenue = cur.fetchone()[0] or 0

        finally:
            cur.close()
            conn.close()

    return render_template(
        "organizer_dashboard.html",
        events=events,
        venues=venues,
        name=session.get("name"),
        notifications=notifications,
        total_events=total_events,
        total_tickets_sold=total_tickets_sold,
        total_revenue=total_revenue,
    )



@app.route("/add_event", methods=["GET", "POST"])
def add_event():
    if session.get("role") != "organizer":
        return redirect("/login/organizer")
    conn = get_connection()
    venues = []
    notifications = get_notifications(session["user_id"])
    selected_venue_id = request.args.get("venue_id", type=int)
    if conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT venue_id, venue_name, city, capacity FROM Venues ORDER BY venue_name"
            )
            venues = cur.fetchall()

            if request.method == "POST":
                name = request.form["name"]
                date = request.form["date"]
                time = request.form.get("time") or None
                price = float(request.form["price"])
                seats = int(request.form["seats"])
                venue_id = int(request.form["venue"])
                selected_venue_id = venue_id

                # Capacity check: seats must not exceed venue capacity
                cur.execute(
                    "SELECT capacity FROM Venues WHERE venue_id = %s",
                    (venue_id,),
                )
                row = cur.fetchone()
                venue_capacity = row[0] if row else 0

                if seats > venue_capacity:
                    flash(f"Total seats cannot exceed venue capacity ({venue_capacity}).")
                    return render_template(
                        "add_event.html",
                        venues=venues,
                        selected_venue_id=selected_venue_id,
                        notifications=notifications,
                    )

                cur.execute(
                    """
                    INSERT INTO Events 
                        (organizer_id, venue_id, event_name, event_date,
                         event_time, price, total_seats, booked_seats)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
                    """,
                    (
                        session["user_id"],
                        venue_id,
                        name,
                        date,
                        time,
                        price,
                        seats,
                    ),
                )
                conn.commit()
                flash("✅ Event created successfully!")
                return redirect("/organizer/dashboard")
        finally:
            cur.close()
            conn.close()
    return render_template(
        "add_event.html",
        venues=venues,
        selected_venue_id=selected_venue_id,
        notifications=notifications,
    )



@app.route("/edit_event/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    if session.get("role") != "organizer":
        return redirect("/login/organizer")
    conn = get_connection()
    if not conn:
        return redirect("/organizer/dashboard")
    cur = conn.cursor()
    notifications = get_notifications(session["user_id"])
    event = None
    venues = []
    try:
        cur.execute("""
            SELECT event_id, event_name, event_date, event_time, price,
                   venue_id, total_seats
            FROM Events 
            WHERE event_id = %s AND organizer_id = %s
        """, (event_id, session["user_id"]))
        event = cur.fetchone()
        if not event:
            flash("Event not found.")
            return redirect("/organizer/dashboard")

        cur.execute("SELECT venue_id, venue_name, city, capacity FROM Venues ORDER BY venue_name")
        venues = cur.fetchall()

        if request.method == "POST":
            name = request.form["name"]
            date = request.form["date"]
            time = request.form.get("time") or None
            price = float(request.form["price"])
            seats = int(request.form["seats"])
            venue_id = int(request.form["venue"])
            cur.execute("""
                UPDATE Events 
                SET event_name=%s, event_date=%s, event_time=%s,
                    price=%s, total_seats=%s, venue_id=%s
                WHERE event_id=%s AND organizer_id=%s
            """, (name, date, time, price, seats, venue_id, event_id, session["user_id"]))
            conn.commit()
            flash("✅ Event updated!")
            return redirect("/organizer/dashboard")
    finally:
        cur.close()
        conn.close()
    return render_template("edit_event.html", event=event, venues=venues, notifications=notifications)



@app.route("/add_venue", methods=["GET", "POST"])
def add_venue():
    if session.get("role") != "organizer":
        return redirect("/login/organizer")
    conn = get_connection()
    venues = []
    notifications = get_notifications(session["user_id"])
    if conn:
        cur = conn.cursor()
        try:
            if request.method == "POST":
                name = request.form["venue_name"]
                address = request.form["address"]
                city = request.form["city"]
                capacity = int(request.form["capacity"])
                cur.execute(
                    """
                    INSERT INTO Venues (venue_name, address, city, capacity, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (name, address, city, capacity, session["user_id"]),
                )
                conn.commit()
                flash("✅ Venue added!")
            cur.execute(
                """
                SELECT venue_id, venue_name, city, capacity 
                FROM Venues 
                ORDER BY venue_id DESC 
                LIMIT 5
                """
            )
            venues = cur.fetchall()
        finally:
            cur.close()
            conn.close()
    return render_template(
        "add_venue.html",
        venues=venues,
        notifications=notifications,
    )



@app.route("/organizer/bookings")
def organizer_bookings():
    if session.get("role") != "organizer":
        return redirect("/login/organizer")
    conn = get_connection()
    bookings = []
    notifications = get_notifications(session["user_id"])
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("""
    SELECT b.booking_id, e.event_name, u.name, b.quantity, b.total_amount, 
           b.status, b.booking_date
    FROM Bookings b 
    JOIN Events e ON b.event_id = e.event_id 
    JOIN Users u ON b.customer_id = u.user_id 
    WHERE e.organizer_id = %s 
    ORDER BY b.booking_date DESC
""", (session["user_id"],))
            bookings = cur.fetchall()
        finally:
            cur.close()
            conn.close()
    return render_template(
        "organizer_bookings.html",
        bookings=bookings,
        notifications=notifications,
    )



@app.route("/delete_event/<int:event_id>")
def delete_event(event_id):
    if session.get("role") != "organizer":
        return redirect("/login/organizer")
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM Bookings WHERE event_id = %s", (event_id,))
            cur.execute(
                "DELETE FROM Events WHERE event_id = %s AND organizer_id = %s",
                (event_id, session["user_id"]),
            )
            conn.commit()
            flash("✅ Event deleted!")
        finally:
            cur.close()
            conn.close()
    return redirect("/organizer/dashboard")



@app.route("/notifications")
def notifications():
    if not session.get("user_id"):
        return redirect("/")
    notifications = get_notifications(session["user_id"])
    return render_template("notifications.html", notifications=notifications)



if __name__ == "__main__":
    app.run(debug=True)
