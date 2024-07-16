from flask import request, jsonify, Blueprint
from .models import db, User, Train, Booking
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import datetime

bp = Blueprint('api', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user = get_jwt_identity()
        user = User.query.filter_by(id=current_user).first()
        if not user.is_admin:
            return jsonify({'message': 'Cannot perform that function!'}), 403
        return f(*args, **kwargs)
    return decorated

@bp.route('/')
def index():
    return jsonify({
        "message": "Welcome to the IRCTC API",
        "endpoints": {
            "register": "/register",
            "login": "/login",
            "add_train": "/train",
            "check_availability": "/availability",
            "book_seat": "/book",
            "get_booking": "/booking/<int:id>"
        }
    })

@bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'New user created!'})

@bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id, expires_delta=datetime.timedelta(minutes=30))
        return jsonify({'token': access_token})
    return jsonify({'message': 'Invalid credentials'}), 401

@bp.route('/train', methods=['POST'])
@jwt_required()
@admin_required
def add_train():
    data = request.get_json()
    new_train = Train(name=data['name'], source=data['source'], destination=data['destination'], total_seats=data['total_seats'], available_seats=data['total_seats'])
    db.session.add(new_train)
    db.session.commit()
    return jsonify({'message': 'New train added!'})

@bp.route('/availability', methods=['GET'])
@jwt_required()
def get_availability():
    source = request.args.get('source')
    destination = request.args.get('destination')
    trains = Train.query.filter_by(source=source, destination=destination).all()
    output = []
    for train in trains:
        train_data = {}
        train_data['name'] = train.name
        train_data['available_seats'] = train.available_seats
        output.append(train_data)
    return jsonify({'trains': output})

@bp.route('/book', methods=['POST'])
@jwt_required()
def book_seat():
    current_user = get_jwt_identity()
    data = request.get_json()
    train = Train.query.filter_by(id=data['train_id']).first()
    if train and train.available_seats > 0:
        train.available_seats -= 1
        booking = Booking(user_id=current_user, train_id=data['train_id'])
        db.session.add(booking)
        db.session.commit()
        return jsonify({'message': 'Seat booked!'})
    return jsonify({'message': 'No seats available!'}), 400

@bp.route('/booking/<int:id>', methods=['GET'])
@jwt_required()
def get_booking(id):
    current_user = get_jwt_identity()
    booking = Booking.query.filter_by(id=id, user_id=current_user).first()
    if not booking:
        return jsonify({'message': 'No booking found!'})
    return jsonify({'booking_id': booking.id, 'train_id': booking.train_id, 'date_booked': booking.date_booked})
