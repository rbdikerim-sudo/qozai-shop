import json
import os
import random
import sqlite3
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import pypdf
import requests

app = Flask(__name__)
app.secret_key = "qozai_secret_key_super_secure"
DATABASE = "database.db"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
  db = getattr(g, "_database", None)
  if db is None:
    db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
  return db


@app.teardown_appcontext
def close_connection(exception):
  db = getattr(g, "_database", None)
  if db is not None:
    db.close()


def init_db():
  with app.app_context():
    db = get_db()
    db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_name TEXT,
                telegram_user TEXT,
                gis_link TEXT,
                kaspi_link TEXT,
                telegram_bot_token TEXT,
                admin_chat_id TEXT,
                admin_password TEXT
            )
        """)
    db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                category TEXT,
                price REAL,
                colors TEXT,
                composition TEXT,
                sizes_en TEXT,
                sizes_ru TEXT,
                image_url TEXT
            )
        """)
    db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_code TEXT,
                author TEXT,
                rating INTEGER,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    default_token = "8249662502:AAFGGDJ1dHgoGikgqDzIcrKZuqeOyjgTXLY".strip()
    default_chat_id = "8107168786".strip()
    default_user = "romaa764".strip()
    default_pass = "qozai_admin_2026"

    row = db.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    if not row:
      db.execute(
          """
                INSERT INTO settings (id, shop_name, telegram_user, gis_link, kaspi_link, telegram_bot_token, admin_chat_id, admin_password) 
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              "QOZAI SHOP",
              default_user,
              "https://2gis.kz",
              "https://kaspi.kz",
              default_token,
              default_chat_id,
              default_pass,
          ),
      )
    else:
      try:
        db.execute(
            "UPDATE settings SET admin_password = COALESCE(admin_password,"
            " 'qozai_admin_2026') WHERE id = 1"
        )
      except:
        pass

    # Демо-товары, если база пустая
    cur = db.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
      demo_products = [
          (
              "CODE-94821",
              "Премиальное худи Oversize",
              "Верхняя одежда",
              34990,
              "Черный, Молочный, Хаки",
              "Хлопок 90%, Полиэстер 10%",
              "S, M, L, XL",
              "44, 46, 48, 50",
              (
                  "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=800&q=80"
              ),
          ),
          (
              "CODE-51234",
              "Классическое поло Lacoste-style",
              "Верхняя одежда",
              18500,
              "Белый, Темно-зеленый, Синий",
              "Пике хлопок 100%",
              "M, L, XL",
              "46, 48, 50",
              (
                  "https://images.unsplash.com/photo-1625910513411-5ed0bd5ae3a9?auto=format&fit=crop&w=800&q=80"
              ),
          ),
      ]
      db.executemany(
          """
                INSERT INTO products (code, name, category, price, colors, composition, sizes_en, sizes_ru, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          demo_products,
      )

    db.commit()


def enrich_products_with_ratings(products_rows):
  db = get_db()
  products = []
  for row in products_rows:
    p = dict(row)
    rev_data = db.execute(
        """
            SELECT AVG(rating) as avg_rating, COUNT(*) as count 
            FROM reviews WHERE product_code = ?
        """,
        (p["code"],),
    ).fetchone()

    if rev_data and rev_data["count"] > 0:
      p["rating"] = round(rev_data["avg_rating"], 1)
      p["reviews_count"] = rev_data["count"]
    else:
      p["rating"] = None
      p["reviews_count"] = 0
    products.append(p)
  return products


@app.route("/")
def index():
  db = get_db()
  settings = dict(
      db.execute("SELECT * FROM settings WHERE id = 1").fetchone() or {}
  )
  category = request.args.get("category", "Все")

  if category == "Все":
    rows = db.execute("SELECT * FROM products").fetchall()
  else:
    rows = db.execute(
        "SELECT * FROM products WHERE category = ?", (category,)
    ).fetchall()

  products = enrich_products_with_ratings(rows)
  categories = [
      "Все",
      "Верхняя одежда",
      "Нижняя одежда",
      "Шапки",
      "Обувь",
      "Аксессуары",
  ]
  has_access = session.get("has_purchased", False) or session.get(
      "admin_logged", False
  )

  return render_template(
      "index.html",
      settings=settings,
      products=products,
      categories=categories,
      current_cat=category,
      has_access=has_access,
  )


@app.route("/cart")
def cart():
  db = get_db()
  settings = dict(
      db.execute("SELECT * FROM settings WHERE id = 1").fetchone() or {}
  )
  return render_template("cart.html", settings=settings)


@app.route("/checkout")
def checkout():
  db = get_db()
  settings = dict(
      db.execute("SELECT * FROM settings WHERE id = 1").fetchone() or {}
  )
  return render_template("checkout.html", settings=settings)


def validate_kaspi_receipt(filepath, ext):
  if ext != "pdf":
    return False
  try:
    reader = pypdf.PdfReader(filepath)
    full_text = ""
    for page in reader.pages:
      full_text += (page.extract_text() or "").lower()

    fiscal_markers = [
        "рнм",
        "знм",
        "фп",
        "kaspi офд",
        "фискальный чек",
        "оплата совершена",
    ]
    found_count = sum(1 for marker in fiscal_markers if marker in full_text)
    return found_count >= 4
  except Exception as e:
    print(f"Ошибка проверки PDF чека: {e}")
    return False


@app.route("/submit_order", methods=["POST"])
def submit_order():
  try:
    db = get_db()
    settings = dict(
        db.execute("SELECT * FROM settings WHERE id = 1").fetchone() or {}
    )

    full_name = request.form.get("full_name", "Не указано")
    address = request.form.get("address", "Не указан")
    whatsapp = request.form.get("whatsapp", "")
    instagram = request.form.get("instagram", "")
    telegram = request.form.get("telegram", "")
    cart_items_json = request.form.get("cart_items", "[]")

    if not whatsapp and not instagram and not telegram:
      return (
          {
              "success": False,
              "error": (
                  "Укажите хотя бы один контакт (WhatsApp, Instagram или"
                  " Telegram)!"
              ),
          },
          400,
      )

    if "receipt" not in request.files:
      return {"success": False, "error": "Не прикреплен чек об оплате!"}, 400

    file = request.files["receipt"]
    if file.filename == "":
      return {"success": False, "error": "Файл чека не выбран."}, 400

    ext = (
        file.filename.rsplit(".", 1)[1].lower()
        if "." in file.filename
        else "jpg"
    )
    filename = f"receipt_{random.randint(10000, 99999)}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    if not validate_kaspi_receipt(filepath, ext):
      if os.path.exists(filepath):
        os.remove(filepath)
      return {
          "success": False,
          "error": (
              "Ошибка проверки! Загруженный файл не является подлинным"
              " фискальным чеком Kaspi (требуется официальный PDF-чек)."
          ),
      }, 400

    try:
      items = json.loads(cart_items_json)
    except:
      items = []

    session["has_purchased"] = True
    purchased_codes = session.get("purchased_codes", [])
    for item in items:
      code = item.get("code")
      if code and code not in purchased_codes:
        purchased_codes.append(code)
    session["purchased_codes"] = purchased_codes

    items_text = ""
    total_price = 0
    for item in items:
      items_text += (
          f"• {item.get('name')} (Код: {item.get('code')})\n  Цвет:"
          f" {item.get('selectedColor')}, Размер:"
          f" {item.get('selectedSize')}\n  Цена: {item.get('price')} ₸\n\n"
      )
      total_price += float(item.get("price", 0))

    message = (
        f"🚨 НОВЫЙ ЗАКАЗ! 🚨\n\n"
        f"👤 ФИО: {full_name}\n"
        f"📍 Адрес: {address}\n"
        f"💬 Контакты:\n"
        f"  - WhatsApp: {whatsapp or '—'}\n"
        f"  - Instagram: {instagram or '—'}\n"
        f"  - Telegram: {telegram or '—'}\n\n"
        f"🛒 Товары:\n{items_text}"
        f"💰 Сумма: {total_price:,.0f} ₸"
    )

    bot_token = str(settings.get("telegram_bot_token", "")).strip()
    admin_chat_id = str(settings.get("admin_chat_id", "")).strip()

    if bot_token and admin_chat_id:
      try:
        url_msg = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(
            url_msg, data={"chat_id": admin_chat_id, "text": message}, timeout=10
        )

        url_doc = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        with open(filepath, "rb") as doc_file:
          requests.post(
              url_doc,
              data={
                  "chat_id": admin_chat_id,
                  "caption": f"📎 Официальный чек от: {full_name}",
              },
              files={"document": doc_file},
              timeout=15,
          )
      except Exception as tg_err:
        print(f"⚠️ Ошибка соединения с Telegram API: {tg_err}")

    return {"success": True, "message": "Заказ успешно отправлен продавцу!"}

  except Exception as e:
    print(f"❌ Критическая ошибка в submit_order: {e}")
    return {"success": False, "error": str(e)}, 500


@app.route("/reviews", methods=["GET", "POST"])
def reviews():
  db = get_db()
  settings = dict(
      db.execute("SELECT * FROM settings WHERE id = 1").fetchone() or {}
  )

  has_access = session.get("has_purchased", False) or session.get(
      "admin_logged", False
  )
  if not has_access:
    flash(
        "Раздел отзывов доступен клиентам после оформления заказа и"
        " администратору.",
        "error",
    )
    return redirect(url_for("index"))

  if request.method == "POST":
    product_code = request.form.get("product_code")
    author = request.form.get("author", "Покупатель")
    rating = int(request.form.get("rating", 5))
    comment = request.form.get("comment", "")

    purchased_codes = session.get("purchased_codes", [])
    is_admin = session.get("admin_logged", False)

    if not is_admin and product_code not in purchased_codes:
      flash("Вы можете оставлять отзывы только на купленные вами товары!", "error")
      return redirect(url_for("reviews"))

    if product_code and comment:
      db.execute(
          """
                INSERT INTO reviews (product_code, author, rating, comment)
                VALUES (?, ?, ?, ?)
            """,
          (product_code, author, rating, comment),
      )
      db.commit()
      flash("Ваш отзыв успешно добавлен!", "success")
    return redirect(url_for("reviews"))

  reviews_list = db.execute("""
        SELECT r.id, r.product_code, r.author, r.rating, r.comment, r.created_at, p.name as product_name, p.image_url 
        FROM reviews r
        LEFT JOIN products p ON r.product_code = p.code
        ORDER BY r.id DESC
    """).fetchall()

  purchased_codes = session.get("purchased_codes", [])
  if session.get("admin_logged", False):
    allowed_products = db.execute("SELECT code, name FROM products").fetchall()
  else:
    if purchased_codes:
      placeholders = ",".join(["?"] * len(purchased_codes))
      allowed_products = db.execute(
          f"SELECT code, name FROM products WHERE code IN ({placeholders})",
          tuple(purchased_codes),
      ).fetchall()
    else:
      allowed_products = []

  return render_template(
      "reviews.html",
      settings=settings,
      reviews=reviews_list,
      allowed_products=allowed_products,
  )


@app.route("/qozai-login-777", methods=["GET", "POST"])
def admin_login():
  db = get_db()
  settings = dict(
      db.execute("SELECT * FROM settings WHERE id = 1").fetchone() or {}
  )
  real_password = settings.get("admin_password") or "qozai_admin_2026"

  if request.method == "POST":
    password = request.form.get("password")
    if password == real_password:
      session["admin_logged"] = True
      return redirect(url_for("admin_panel"))
    else:
      return render_template("login.html", error="Неверный пароль!")
  return render_template("login.html")


@app.route("/qozai-secure-admin-999", methods=["GET", "POST"])
def admin_panel():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  db = get_db()
  if request.method == "POST":
    action = request.form.get("action")

    if action == "update_settings":
      shop_name = request.form.get("shop_name")
      telegram_user = request.form.get("telegram_user")
      gis_link = request.form.get("gis_link")
      kaspi_link = request.form.get("kaspi_link")
      telegram_bot_token = request.form.get("telegram_bot_token").strip()
      admin_chat_id = request.form.get("admin_chat_id").strip()

      db.execute(
          """
                UPDATE settings 
                SET shop_name = ?, telegram_user = ?, gis_link = ?, kaspi_link = ?, telegram_bot_token = ?, admin_chat_id = ?
                WHERE id = 1
            """,
          (
              shop_name,
              telegram_user,
              gis_link,
              kaspi_link,
              telegram_bot_token,
              admin_chat_id,
          ),
      )
      db.commit()
      flash("Настройки успешно обновлены!", "success")

    elif action == "update_password":
      old_pass = request.form.get("old_password")
      new_pass = request.form.get("new_password")
      confirm_pass = request.form.get("confirm_password")

      settings = dict(
          db.execute("SELECT * FROM settings WHERE id = 1").fetchone() or {}
      )
      current_pass = settings.get("admin_password") or "qozai_admin_2026"

      if old_pass != current_pass:
        flash("Старый пароль введен неверно!", "error")
      elif new_pass != confirm_pass:
        flash("Новые пароли не совпадают!", "error")
      elif not new_pass:
        flash("Новый пароль не может быть пустым!", "error")
      else:
        db.execute(
            "UPDATE settings SET admin_password = ? WHERE id = 1", (new_pass,)
        )
        db.commit()
        flash("Пароль администратора успешно изменен!", "success")

    elif action == "add_product":
      name = request.form.get("name")
      category = request.form.get("category")
      price = request.form.get("price")
      colors = request.form.get("colors")
      composition = request.form.get("composition")
      sizes_en = request.form.get("sizes_en")
      sizes_ru = request.form.get("sizes_ru")
      code = f"CODE-{random.randint(10000, 99999)}"

      # ИЗМЕНЕНИЕ: Обработка загрузки файла фото из устройства вместо текстовой ссылки
      image_url = ""
      if "image_file" in request.files:
        file = request.files["image_file"]
        if file and file.filename != "":
          ext = (
              file.filename.rsplit(".", 1)[1].lower()
              if "." in file.filename
              else "jpg"
          )
          filename = f"prod_{random.randint(10000, 99999)}.{ext}"
          filepath = os.path.join(UPLOAD_FOLDER, filename)
          file.save(filepath)
          image_url = f"static/uploads/{filename}"

      db.execute(
          """
                INSERT INTO products (code, name, category, price, colors, composition, sizes_en, sizes_ru, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              code,
              name,
              category,
              price,
              colors,
              composition,
              sizes_en,
              sizes_ru,
              image_url,
          ),
      )
      db.commit()
      flash("Товар успешно добавлен!", "success")

    elif action == "delete_product":
      prod_id = request.form.get("product_id")
      db.execute("DELETE FROM products WHERE id = ?", (prod_id,))
      db.commit()
      flash("Товар удален!", "success")

    return redirect(url_for("admin_panel"))

  settings = dict(
      db.execute("SELECT * FROM settings WHERE id = 1").fetchone() or {}
  )
  products = [dict(row) for row in db.execute("SELECT * FROM products").fetchall()]
  return render_template("admin.html", settings=settings, products=products)


@app.route("/admin-logout")
def admin_logout():
  session.pop("admin_logged", None)
  return redirect("/")


if __name__ == "__main__":
  init_db()
  app.run(debug=True)