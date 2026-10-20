import os
import json
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from PIL import Image

app = Flask(__name__)
app.secret_key = 'qozai_shop_super_secret_key_change_me'

UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'items.json'
CONFIG_FILE = 'config.json'
REVIEWS_FILE = 'reviews.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEFAULT_CONFIG = {
    "telegram_token": "8867412750:AAFrtst2I-g2XqiH6i8oJDMq5Kop3OsM4U0",
    "telegram_chat_id": "8107168786",
    "admin_password": "admin"
}

DEFAULT_ITEMS = []

def load_items():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_ITEMS

def save_items(items):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=4)

def load_reviews():
    if os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_reviews(reviews):
    with open(REVIEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data.get("telegram_token"):
                data["telegram_token"] = DEFAULT_CONFIG["telegram_token"]
            if not data.get("telegram_chat_id"):
                data["telegram_chat_id"] = DEFAULT_CONFIG["telegram_chat_id"]
            if not data.get("admin_password"):
                data["admin_password"] = DEFAULT_CONFIG["admin_password"]
            return data
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def remove_white_background(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        if item[0] > 230 and item[1] > 230 and item[2] > 230:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(output_path, "PNG")

def validate_receipt(file_path):
    try:
        if file_path.lower().endswith('.pdf'):
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False, "Загруженный файл не является корректным PDF-документом."
            return True, "Успешно"
        else:
            with Image.open(file_path) as img:
                width, height = img.size
                if height <= width:
                    return False, "Загруженный файл не похож на вертикальный чек (изображение должно быть вертикальным)."
                if width < 200 or height < 300:
                    return False, "Слишком низкое разрешение изображения чека."
            return True, "Успешно"
    except Exception:
        return False, "Ошибка чтения файла чека."

@app.route('/')
def index():
    items = load_items()
    return render_template('index.html', items=items)

@app.route('/reviews')
def reviews_page():
    reviews = load_reviews()
    return render_template('reviews.html', reviews=reviews)

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/checkout')
def checkout_page():
    return render_template('checkout.html')

@app.route('/place-order', methods=['POST'])
def place_order():
    try:
        fio = request.form.get('fio')
        whatsapp = request.form.get('whatsapp', '').strip()
        instagram = request.form.get('instagram', '').strip()
        telegram = request.form.get('telegram', '').strip()
        address = request.form.get('address')
        items_json = request.form.get('items')
        
        if not whatsapp and not instagram and not telegram:
            return jsonify({"status": "error", "message": "Укажите хотя бы один способ связи!"}), 400

        receipt_file = request.files.get('receipt')
        if not receipt_file or not receipt_file.filename:
            return jsonify({"status": "error", "message": "Загрузите чек об оплате!"}), 400

        file_ext = os.path.splitext(receipt_file.filename)[1].lower()
        if file_ext not in ['.png', '.jpg', '.jpeg', '.pdf']:
            return jsonify({"status": "error", "message": "Недопустимый формат файла. Загрузите фото или PDF."}), 400

        receipt_filename = f"receipt_{os.urandom(4).hex()}{file_ext}"
        receipt_path = os.path.join(UPLOAD_FOLDER, receipt_filename)
        receipt_file.save(receipt_path)

        is_valid, err_msg = validate_receipt(receipt_path)
        if not is_valid:
            if os.path.exists(receipt_path):
                os.remove(receipt_path)
            return jsonify({"status": "error", "message": f"Ошибка проверки чека: {err_msg}"}), 400

        selected_items = json.loads(items_json) if items_json else []
        items_text = ""
        total_sum = 0
        
        for item in selected_items:
            size_str = f" [Размер: {item.get('size', 'Не указан')}]" if item.get('size') else ""
            items_text += f"- {item['title']}{size_str} — {item['price_formatted']}\n"
            try:
                total_sum += int(str(item['price']).replace(' ', '').replace('₸', ''))
            except:
                pass

        contacts_str = ""
        if whatsapp: contacts_str += f"\nWhatsApp: {whatsapp}"
        if instagram: contacts_str += f"\nInstagram: {instagram}"
        if telegram: contacts_str += f"\nTelegram: {telegram}"

        message = (
            f"НОВЫЙ ЗАКАЗ QOZAI SHOP!\n\n"
            f"ФИО: {fio}\n"
            f"Контакты:{contacts_str}\n"
            f"Адрес: {address}\n\n"
            f"Выбранные товары:\n{items_text}\n"
            f"Итого к оплате: {total_sum:,} ₸\n"
            f"Получатель: @romaa764"
        )

        config = load_config()
        token = config.get("telegram_token", DEFAULT_CONFIG["telegram_token"])
        chat_id = config.get("telegram_chat_id", DEFAULT_CONFIG["telegram_chat_id"])

        if token and chat_id:
            if file_ext == '.pdf':
                url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
                with open(receipt_path, 'rb') as doc:
                    files = {'document': doc}
                    data = {'chat_id': chat_id, 'caption': message}
                    requests.post(url_doc, data=data, files=files)
            else:
                url_photo = f"https://api.telegram.org/bot{token}/sendPhoto"
                with open(receipt_path, 'rb') as photo:
                    files = {'photo': photo}
                    data = {'chat_id': chat_id, 'caption': message}
                    requests.post(url_photo, data=data, files=files)

        return jsonify({"status": "success", "message": "Заказ успешно оформлен!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None
    config = load_config()
    if request.method == 'POST':
        password = request.form.get('password')
        if password == config.get('admin_password', 'admin'):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = 'Неверный пароль!'
    return render_template('login.html', error=error)

@app.route('/admin-logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    config = load_config()
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'save_config':
            token = request.form.get('telegram_token')
            chat_id = request.form.get('telegram_chat_id')
            new_pass = request.form.get('admin_password')
            
            config['telegram_token'] = token
            config['telegram_chat_id'] = chat_id
            if new_pass:
                config['admin_password'] = new_pass
            save_config(config)
            
            qr_file = request.files.get('kaspi_qr')
            if qr_file and qr_file.filename:
                qr_path = os.path.join('static', 'kaspi_qr.png')
                qr_file.save(qr_path)
                
            return redirect(url_for('admin'))
        
        elif action == 'add_review':
            review_file = request.files.get('review_image')
            review_text = request.form.get('review_text', '')
            if review_file and review_file.filename:
                filename = f"review_{os.urandom(4).hex()}.png"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                review_file.save(filepath)
                
                reviews = load_reviews()
                reviews.insert(0, {
                    "image": filename,
                    "text": review_text
                })
                save_reviews(reviews)
            return redirect(url_for('admin'))
        
        title = request.form.get('title')
        price_raw = request.form.get('price')
        price_formatted = f"{int(price_raw):,} ₸" if price_raw.isdigit() else price_raw
        badge = request.form.get('badge', '')
        sizes = request.form.get('sizes', 'S, M, L')
        colors = request.form.get('colors', 'Стандарт')
        specs = request.form.get('specs', '100% хлопок')
        file = request.files.get('image')
        
        if file and file.filename:
            filename = f"clothing_{os.urandom(4).hex()}.png"
            temp_path = os.path.join(UPLOAD_FOLDER, 'temp_' + filename)
            final_path = os.path.join(UPLOAD_FOLDER, filename)
            
            file.save(temp_path)
            remove_white_background(temp_path, final_path)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            items = load_items()
            new_item = {
                "id": len(items) + 1,
                "title": title,
                "price": price_raw,
                "price_formatted": price_formatted,
                "badge": badge,
                "sizes": sizes,
                "colors": colors,
                "specs": specs,
                "image": filename
            }
            items.append(new_item)
            save_items(items)
            
        return redirect(url_for('admin'))
        
    return render_template('admin.html', config=config)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
