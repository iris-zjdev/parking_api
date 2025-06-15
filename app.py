from flask import Flask, request, jsonify
import json
import psycopg2
from db_config import DB_CONFIG

app = Flask(__name__)

with open("device_auth.json", "r") as f:
    AUTH_WHITELIST = json.load(f)

def check_device_auth():
    device_id = request.headers.get("X-Device-ID")
    api_key = request.headers.get("X-API-Key")
    if not device_id or not api_key:
        return False, "Missing headers"
    
    valid_key = AUTH_WHITELIST.get(device_id)
    if valid_key != api_key:
        return False, "Unauthorized device"
    
    return True, None

@app.route('/api/park', methods=['POST'])
def park():
    auth_status, msg = check_device_auth()
    if not auth_status:
        return jsonify({"error": msg}), 403
    
    data = request.json
    rfid = data.get('rfid')
    username = data.get('username')
    car_id = data.get('car_id')

    if not all([rfid, username, car_id]):
        return jsonify({"error": "Missing rfid, username or car_id"}), 400

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # first time user
        cursor.execute("""
            INSERT INTO user_info (rfid, username, car_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (rfid) DO NOTHING;
        """, (rfid, username, car_id))

        # only one parking limit
        cursor.execute("SELECT * FROM spot WHERE occupied_car_id = %s", (car_id,))
        if cursor.fetchone():
            return jsonify({"message": "Car is already parked"}), 200

        # search available spots
        cursor.execute("SELECT spot_id FROM spot WHERE is_occupied = FALSE LIMIT 1")
        spot = cursor.fetchone()
        if not spot:
            return jsonify({"message": "No available spot"}), 200

        spot_id = spot[0]
        cursor.execute("""
            UPDATE spot
            SET is_occupied = TRUE, occupied_car_id = %s
            WHERE spot_id = %s
        """, (car_id, spot_id))
        conn.commit()

        return jsonify({"message": "Parked successfully", "spot": spot_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()


@app.route('/api/unpark', methods=['POST'])
def unpark():
    auth_status, msg = check_device_auth()
    if not auth_status:
        return jsonify({"error": msg}), 403
    
    rfid = request.json.get('rfid')
    if not rfid:
        return jsonify({"error": "Missing RFID"}), 400

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT car_id FROM user_info WHERE rfid = %s", (rfid,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "User not found"}), 404

        car_id = result[0]

        cursor.execute("SELECT spot_id FROM spot WHERE occupied_car_id = %s", (car_id,))
        spot = cursor.fetchone()
        if not spot:
            return jsonify({"message": "Car is not parked"}), 200

        cursor.execute("""
            UPDATE spot
            SET is_occupied = FALSE, occupied_car_id = NULL
            WHERE occupied_car_id = %s
        """, (car_id,))
        conn.commit()
        return jsonify({"message": "Unparked successfully", "spot": spot[0]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()


@app.route('/api/status', methods=['GET'])
def status():
    auth_status, msg = check_device_auth()
    if not auth_status:
        return jsonify({"error": msg}), 403

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT spot_id, is_occupied, occupied_car_id FROM spot ORDER BY spot_id")
        data = cursor.fetchall()
        result = [
            {"spot_id": row[0], "is_occupied": row[1], "occupied_car_id": row[2]}
            for row in data
        ]
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/api/query_user', methods=['POST'])
def query_user():
    auth_status, msg = check_device_auth()
    if not auth_status:
        return jsonify({"error": msg}), 403

    rfid = request.json.get('rfid')
    if not rfid:
        return jsonify({"error": "Missing RFID"}), 400

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT username, car_id FROM user_info WHERE rfid = %s", (rfid,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404

        username, car_id = user

        cursor.execute("SELECT spot_id FROM spot WHERE occupied_car_id = %s", (car_id,))
        spot = cursor.fetchone()
        if spot:
            return jsonify({
                "username": username,
                "car_id": car_id,
                "parked": True,
                "spot": spot[0]
            })
        else:
            return jsonify({
                "username": username,
                "car_id": car_id,
                "parked": False,
                "spot": None
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/api/users', methods=['GET'])
def list_users():
    auth_status, msg = check_device_auth()
    if not auth_status:
        return jsonify({"error": msg}), 403

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.username, u.rfid, s.spot_id
            FROM user_info u
            LEFT JOIN spot s ON u.car_id = s.occupied_car_id
            ORDER BY u.username
        """)
        data = cursor.fetchall()

        result = [
            {
                "rfid": row[1],
                "username": row[0],
                "is_parked": row[2] is not None,
                "spot_id": row[2]
            }
            for row in data
        ]
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)


# from flask import Flask, request, jsonify
# from db_config import engine
# from sqlalchemy import text
# import os

# app = Flask(__name__)

# @app.route('/api/park', methods=['POST'])
# def park():
#     data = request.json
#     rfid = data.get('rfid')
#     username = data.get('username')
#     car_id = data.get('car_id')

#     if not all([rfid, username, car_id]):
#         return jsonify({"error": "Missing rfid, username or car_id"}), 400

#     try:
#         with engine.begin() as conn:
#             conn.execute(text("""
#                 INSERT INTO user_info (rfid, username, car_id)
#                 VALUES (:rfid, :username, :car_id)
#                 ON CONFLICT (rfid) DO NOTHING;
#             """), {"rfid": rfid, "username": username, "car_id": car_id})

#             result = conn.execute(text("SELECT * FROM spot WHERE occupied_car_id = :car_id"),
#                                   {"car_id": car_id}).fetchone()
#             if result:
#                 return jsonify({"message": "Car is already parked"}), 200

#             spot = conn.execute(text("SELECT spot_id FROM spot WHERE is_occupied = FALSE LIMIT 1")).fetchone()
#             if not spot:
#                 return jsonify({"message": "No available spot"}), 200

#             conn.execute(text("""
#                 UPDATE spot
#                 SET is_occupied = TRUE, occupied_car_id = :car_id
#                 WHERE spot_id = :spot_id
#             """), {"car_id": car_id, "spot_id": spot[0]})

#             return jsonify({"message": "Parked successfully", "spot": spot[0]})

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/api/unpark', methods=['POST'])
# def unpark():
#     rfid = request.json.get('rfid')
#     if not rfid:
#         return jsonify({"error": "Missing RFID"}), 400

#     try:
#         with engine.begin() as conn:
#             user = conn.execute(text("SELECT car_id FROM user_info WHERE rfid = :rfid"),
#                                 {"rfid": rfid}).fetchone()
#             if not user:
#                 return jsonify({"error": "User not found"}), 404

#             car_id = user[0]
#             spot = conn.execute(text("SELECT spot_id FROM spot WHERE occupied_car_id = :car_id"),
#                                 {"car_id": car_id}).fetchone()
#             if not spot:
#                 return jsonify({"message": "Car is not parked"}), 200

#             conn.execute(text("""
#                 UPDATE spot
#                 SET is_occupied = FALSE, occupied_car_id = NULL
#                 WHERE occupied_car_id = :car_id
#             """), {"car_id": car_id})

#             return jsonify({"message": "Unparked successfully", "spot": spot[0]})

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/api/status', methods=['GET'])
# def status():
#     try:
#         with engine.begin() as conn:
#             data = conn.execute(text("SELECT spot_id, is_occupied, occupied_car_id FROM spot ORDER BY spot_id")).fetchall()
#             result = [
#                 {"spot_id": row[0], "is_occupied": row[1], "occupied_car_id": row[2]}
#                 for row in data
#             ]
#             return jsonify(result)

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/api/query_user', methods=['POST'])
# def query_user():
#     rfid = request.json.get('rfid')
#     if not rfid:
#         return jsonify({"error": "Missing RFID"}), 400

#     try:
#         with engine.begin() as conn:
#             user = conn.execute(text("SELECT username, car_id FROM user_info WHERE rfid = :rfid"),
#                                 {"rfid": rfid}).fetchone()
#             if not user:
#                 return jsonify({"error": "User not found"}), 404

#             username, car_id = user
#             spot = conn.execute(text("SELECT spot_id FROM spot WHERE occupied_car_id = :car_id"),
#                                 {"car_id": car_id}).fetchone()

#             return jsonify({
#                 "username": username,
#                 "car_id": car_id,
#                 "parked": bool(spot),
#                 "spot": spot[0] if spot else None
#             })

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# if __name__ == '__main__':
#     port = int(os.environ.get("PORT", 5050))
#     app.run(host="0.0.0.0", port=port)

