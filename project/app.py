from flask import Flask, send_file, request, render_template, jsonify
import json
import os
import uuid
from werkzeug.routing import BaseConverter

app = Flask(__name__)
class UUID(BaseConverter):
    regex = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
app.url_map.converters['uuid'] = UUID
app.config['TEMPLATES_AUTO_RELOAD'] = True

DATA_PATH = './data/'

def load_data(filename):
    with open(os.path.join(DATA_PATH, filename), 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(filename, data):
    with open(os.path.join(DATA_PATH, filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@app.route('/login', methods=['POST'])
def login():
    user = request.get_json()
    travellers = load_data('travellers.json')
    bookings = load_data('bookings.json')

    traveller = next((p for p in travellers if p['username'] == user['username'] and p['password'] == user['password']), None)
    if traveller:
        booking = next((b for b in bookings if b['travellerId'] == traveller['id']), None)
        if booking:
            return jsonify(success=True, tourId=booking['tourId'])
    return jsonify(success=False)

@app.route('/register', methods=['POST'])
def register():
    user = request.get_json()
    travellers = load_data('travellers.json')
    bookings = load_data('bookings.json')

    traveller_id = str(uuid.uuid4())
    booking_id = str(uuid.uuid4())

    new_traveller = {
        'id': traveller_id,
        'username': user['username'],
        'password': user['password'],
        'firstname': user.get('firstname', ''),
        'lastname': user.get('lastname', ''),
        'patronymic': user.get('patronymic', ''),
        'birthdate': user.get('birthdate', ''),
        'series': user.get('series', '')
    }
    travellers.append(new_traveller)
    save_data('travellers.json', travellers)

    new_booking = {
        'id': booking_id,
        'travellerId': traveller_id,
        'tourId': None,
        'isRegistered': False,
        'seat': None
    }
    bookings.append(new_booking)
    save_data('bookings.json', bookings)

    return '', 200

@app.route('/api/bookings/<uuid:id>')
def get_tour(id) -> str:
    bookings = load_data('bookings.json')
    tours = load_data('tours.json')
    travellers = load_data('travellers.json')

    booking = next((b for b in bookings if b['id'] == str(id)), None)
    if not booking:
        return 'Бронювання не знайдено', 404

    tour = next((f for f in tours if f['id'] == booking['tourId']), {})
    traveller = next((p for p in travellers if p['id'] == booking['travellerId']), {})

    result = {
        **booking,
        'tour': tour,
        'traveller': traveller
    }
    return result

@app.route('/api/travellers/<uuid:id>')
def get_traveller(id) -> str:
    travellers = load_data('travellers.json')
    traveller = next((p for p in travellers if p['id'] == str(id)), None)
    return traveller if traveller else ('Traveller not found', 404)

@app.route('/api/travellers/validate', methods=['POST'])
def validate_traveller() -> str:
    data = request.get_json()
    travellers = load_data('travellers.json')

    traveller = next((p for p in travellers if
                      p['firstname'] == data['firstname'] and
                      p['lastname'] == data['lastname'] and
                      p['patronymic'] == data['patronymic'] and
                      p['birthdate'] == data['birthdate'] and
                      p['series'] == data['series']), None)
    return 'True' if traveller else 'False'

# Complete traveller registration
@app.route('/api/bookings/<uuid:id>', methods=['POST'])
def finish_registration(id) -> str:
    data = request.get_json()
    bookings = load_data('bookings.json')

    for booking in bookings:
        if booking['id'] == str(id):
            booking['isRegistered'] = True
            booking['seat'] = int(data['seat'])
            save_data('bookings.json', bookings)

            route_list = get_tour(id)
            with open(f'./{id}.txt', 'w') as f:
                f.write(str(route_list))
            return 'True'

    return 'Бронювання не знайдено', 404

# Return form for entering passport data
@app.route('/passport')
def passport():
    context = {}
    context['id'] = request.args['tour']
    return render_template('passport.html', context=context)

# Return interface for starting registration
@app.route('/booking')
def booking():
    tour_id = request.args.get('tour')
    if not tour_id:
        return 'Потрібен ідентифікатор Туру', 400

    bookings = load_data('bookings.json')
    tours = load_data('tours.json')
    travellers = load_data('travellers.json')

    booking = next((b for b in bookings if b['id'] == tour_id), None)
    if not booking:
        return 'Booking not found', 404

    tour = next((f for f in tours if f['id'] == booking['tourId']), {})
    traveller = next((p for p in travellers if p['id'] == booking['travellerId']), {})

    context = {
        'id': booking['id'],
        'company': 'Lufthasa',
        'path': f"{tour.get('origin', '')} - {tour.get('destination', '')}",
        'from': tour.get('origin', ''),
        'to': tour.get('destination', ''),
        'timefrom': tour.get('departureTime', ''),
        'timeto': tour.get('arrivalTime', ''),
        'firstname': traveller.get('firstname', ''),
        'lastname': traveller.get('lastname', ''),
        'patronymic': traveller.get('patronymic', ''),
    }

    return render_template('booking.html', context=context)

# Return form for seat selection
@app.route('/seat')
def seat():
    context = {}
    bookings = load_data('bookings.json')
    context['id'] = request.args['tour']
    tour_id = next((b['tourId'] for b in bookings if b['id'] == context['id']), None)
    if not tour_id:
        return 'Tour not found', 404

    occupied_seats = [b['seat'] for b in bookings if b['tourId'] == tour_id and b['seat'] is not None]
    context['seats'] = [True] * 256
    for seat in occupied_seats:
        context['seats'][seat] = False
    return render_template('seat.html', context=context)

# Return form for entering booking number (main page)
@app.route('/')
def main():
    return render_template('main.html')

@app.route('/route')
def route():
    context = {}
    context['id'] = request.args['tour']
    tours = load_data('tours.json')
    tour = next((f for f in tours if f['id'] == context['id']), None)
    if not tour:
        return 'Tour not found', 404
    context['origin'] = tour['origin']
    context['destination'] = tour['destination']
    context['departureTime'] = tour['departureTime']
    context['arrivalTime'] = tour['arrivalTime']
    return render_template('route.html', context=context)

@app.route('/choose_route')
def choose_route():
    tours = load_data('tours.json')
    return render_template('choose_route.html', tours=tours)

@app.route('/download/<uuid:id>')
def download(id):
    file_path = f'./{id}'
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, attachment_filename=f'{id}')
    else:
        return 'File not found', 404

if __name__ == '__main__':
    app.run(debug=False, port=3400)
