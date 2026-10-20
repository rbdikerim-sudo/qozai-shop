import os
import json
import requests
from PIL import Image
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'qozai_shop_super_secret_key_change_me'

UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'items.json'
CONFIG_FILE = 'config.json'
REVIEWS_FILE = 'reviews.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEFAULT_CONFIG = {
    "telegram_token": "",
    "telegram_chat_id": "",
    "admin_password": "admin",
    "gis_link": "https://2gis.kz",
    "payment_link": "https://pay.kaspi.kz"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    return DEFAULT_CONFIG

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)

def load_items():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

@app.route('/')
def index():
    items = load_items()
    config = load_config()
    return render_template('index.html', items=items, config=config)

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    config = load_config()
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    items = load_items()
    if request.method == 'POST':
        title = request.form.get('title')
        price = request.form.get('price')
        sizes = request.form.get('sizes')
        colors = request.form.get('colors')
        specs = request.form.get('specs')
        file = request.files.get('image')

        image_filename = ''
        if file and file.filename:
            import uuid
            try:
                # Автоматическое удаление белого фона через Pillow
                img = Image.open(file.stream).convert("RGBA")
                data = img.getdata()
                new_data = []
                for item in data:
                    if item[0] > 220 and item[1] > 220 and item[2] > 220:
                        new_data.append((255, 255, 255, 0))
                    else:
                        new_data.append(item)
                img.putdata(new_data)
                
                image_filename = f"clothing_{uuid.uuid4().hex[:8]}.png"
                filepath = os.path.join(UPLOAD_FOLDER, image_filename)
                img.save(filepath, "PNG")
            except Exception as e:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
                image_filename = f"clothing_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, image_filename)
                file.save(filepath)

        new_item = {
            "id": items[-1]['id'] + 1 if items else 1,
            "title": title,
            "price": price,
            "price_formatted": f"{int(price):,} ₸".replace(',', ' ') if price and price.isdigit() else price + " ₸",
            "sizes": sizes,
            "colors": colors,
            "specs": specs,
            "image": image_filename
        }
        items.append(new_item)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=4)
        return redirect(url_for('admin_panel'))

    return render_template('admin.html', items=items, config=config)

@app.route('/admin/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    items = load_items()
    updated_items = []
    for item in items:
        if item.get('id') == item_id:
            img_name = item.get('image')
            if img_name:
                img_path = os.path.join(UPLOAD_FOLDER, img_name)
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except:
                        pass
        else:
            updated_items.append(item)
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(updated_items, f, ensure_ascii=False, indent=4)
    return redirect(url_for('admin_panel'))

@app.route('/update-config', methods=['POST'])
def update_config():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    config = load_config()
    config['gis_link'] = request.form.get('gis_link', config['gis_link'])
    config['payment_link'] = request.form.get('payment_link', config['payment_link'])
    config['telegram_token'] = request.form.get('telegram_token', config['telegram_token'])
    config['telegram_chat_id'] = request.form.get('telegram_chat_id', config['telegram_chat_id'])
    config['admin_password'] = request.form.get('admin_password', config['admin_password'])
    save_config(config)
    return redirect(url_for('admin_panel'))

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    config = load_config()
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == config.get('admin_password', 'admin'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = 'Неверный пароль'
    return render_template('login.html', error=error)

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/cart')
def cart():
    config = load_config()
    cart_items = session.get('cart', [])
    items = load_items()
    valid_identifiers = {(str(i.get('id')), i.get('title')) for i in items}
    
    # Очищаем корзину от товаров, которые были удалены из каталога
    cleaned_cart = [ci for ci in cart_items if (str(ci.get('id')), ci.get('title')) in valid_identifiers]
    session['cart'] = cleaned_cart
    return render_template('cart.html', cart_items=cleaned_cart, config=config)

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    data = request.json
    item_id = data.get('id')
    size = data.get('size')
    items = load_items()
    target_item = next((i for i in items if i.get('id') == item_id), None)
    if target_item:
        cart = session.get('cart', [])
        cart.append({
            "id": target_item['id'],
            "title": target_item['title'],
            "price": target_item.get('price_formatted', target_item['price']),
            "size": size,
            "image": target_item['image']
        })
        session['cart'] = cart
        return jsonify({"success": True, "count": len(cart)})
    return jsonify({"success": False}), 400

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    config = load_config()
    if request.method == 'POST':
        name = request.form.get('name')
        whatsapp = request.form.get('whatsapp')
        instagram = request.form.get('instagram')
        telegram_acc = request.form.get('telegram')
        address = request.form.get('address')
        receipt_file = request.files.get('receipt')
        
        cart_items = session.get('cart', [])
        
        token = config.get('telegram_token')
        chat_id = config.get('telegram_chat_id')
        
        if token and chat_id:
            cart_text = "\n".join([f"- {i['title']} (Размер: {i['size']}, Цена: {i['price']})" for i in cart_items])
            message = f"🛍 Новый заказ в Qozai Shop!\n\n👤 Имя: {name}\n💬 WhatsApp: {whatsapp}\n📸 Instagram: {instagram}\n✈️ Telegram: {telegram_acc}\n📍 Адрес: {address}\n\n📦 Товары:\n{cart_text}"
            
            try:
                if receipt_file and receipt_file.filename:
                    receipt_path = os.path.join(UPLOAD_FOLDER, f"receipt_{receipt_file.filename}")
                    receipt_file.save(receipt_path)
                    with open(receipt_path, 'rb') as photo:
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendPhoto",
                            data={"chat_id": chat_id, "caption": message},
                            files={"photo": photo}
                        )
                else:
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat_id, "text": message}
                    )
            except Exception as e:
                print("Telegram error:", e)

        session['cart'] = []
        return render_template('checkout.html', success=True, config=config)
        
    return render_template('checkout.html', success=False, config=config)

@app.route('/reviews')
def reviews():
    config = load_config()
    reviews_list = []
    if os.path.exists(REVIEWS_FILE):
        with open(REVIEWS_FILE, 'r', encoding='utf-8') as f:
            try:
                reviews_list = json.load(f)
            except:
                pass
    return render_template('reviews.html', reviews=reviews_list, config=config)

if __name__ == '__main__':
    app.run(debug=True)