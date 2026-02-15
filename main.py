# main.py - ПОЛНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ
from fastapi import FastAPI, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from datetime import datetime
import os
import shutil
import hashlib
import json

# Создаем папки
os.makedirs("static/uploads/products", exist_ok=True)
os.makedirs("static/uploads/categories", exist_ok=True)
os.makedirs("static/uploads/team", exist_ok=True)
os.makedirs("templates/admin", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

app = FastAPI(title="Королевские Жалюзи - Премиум производство")

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ===== ДОБАВЛЯЕМ ФИЛЬТР from_json ДЛЯ JINJA2 =====
def from_json(value):
    """Преобразует JSON строку в объект Python"""
    if not value:
        return []
    try:
        return json.loads(value)
    except:
        return []

# Регистрируем фильтр в Jinja2
templates.env.filters['from_json'] = from_json

# База данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./royal_blinds.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===== МОДЕЛИ =====

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.now)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text)
    image = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, unique=True, index=True)
    name = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"))
    description = Column(Text)
    price = Column(Float, nullable=True)
    image = Column(String, nullable=True)
    images = Column(Text, nullable=True)
    material = Column(String, nullable=True)
    sizes = Column(String, nullable=True)
    in_stock = Column(Boolean, default=True)
    is_popular = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    category = relationship("Category", back_populates="products")

class Installer(Base):
    __tablename__ = "installers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    orders = relationship("Order", back_populates="installer")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    client_name = Column(String, nullable=False)
    client_phone = Column(String, nullable=False)
    
    # Категории
    category_plisse = Column(Boolean, default=False)
    category_daynight = Column(Boolean, default=False)
    category_mini = Column(Boolean, default=False)
    
    # JSON данные для множественных позиций
    plisse_items = Column(Text, nullable=True, default="[]")  # JSON массив позиций Плиссе
    daynight_items = Column(Text, nullable=True, default="[]")  # JSON массив позиций День и Ночь
    mini_items = Column(Text, nullable=True, default="[]")  # JSON массив позиций Мини
    
    # Общие суммы
    total_sum = Column(Float, default=0.0)
    
    # Установщик
    installer_id = Column(Integer, ForeignKey("installers.id"), nullable=True)
    installer_phone = Column(String, nullable=True)
    installer_username = Column(String, nullable=True)
    
    # Статусы
    status = Column(String, default='pending')
    payment_status = Column(String, default='unpaid')
    
    # Даты
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Связи
    installer = relationship("Installer", back_populates="orders")

# ===== СОЗДАНИЕ ТАБЛИЦ =====
Base.metadata.create_all(bind=engine)

# ===== АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ТАБЛИЦ =====
def upgrade_database():
    """Добавляет новые колонки в существующие таблицы"""
    inspector = inspect(engine)
    
    if inspector.has_table("orders"):
        existing_columns = [col['name'] for col in inspector.get_columns("orders")]
        
        new_columns = {
            'plisse_items': "ALTER TABLE orders ADD COLUMN plisse_items TEXT DEFAULT '[]'",
            'daynight_items': "ALTER TABLE orders ADD COLUMN daynight_items TEXT DEFAULT '[]'",
            'mini_items': "ALTER TABLE orders ADD COLUMN mini_items TEXT DEFAULT '[]'"
        }
        
        for col_name, sql in new_columns.items():
            if col_name not in existing_columns:
                try:
                    with engine.connect() as conn:
                        conn.execute(text(sql))
                        conn.commit()
                        print(f"✅ Добавлена колонка: {col_name}")
                except Exception as e:
                    print(f"⚠️ Не удалось добавить {col_name}: {e}")

# Запускаем обновление
upgrade_database()

# Проверяем и создаем новые таблицы
def create_new_tables():
    inspector = inspect(engine)
    if not inspector.has_table("installers"):
        Installer.__table__.create(bind=engine)
        print("✅ Таблица 'installers' создана")
    if not inspector.has_table("orders"):
        Order.__table__.create(bind=engine)
        print("✅ Таблица 'orders' создана")

create_new_tables()

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_admin(db: Session):
    admin = db.query(Admin).filter(Admin.username == "admin").first()
    if not admin:
        admin = Admin(
            username="admin",
            password_hash=hash_password("admin123")
        )
        db.add(admin)
        db.commit()
        print("✅ Администратор создан: admin / admin123")

def check_admin_auth(request: Request):
    admin_id = request.cookies.get("admin_id")
    return bool(admin_id)

# ===== СТАТИЧЕСКИЕ ФАЙЛЫ =====
@app.get("/static/js/whatsapp.js")
async def whatsapp_js():
    return Response(
        content="""
        function openWhatsApp(sku = '', name = '', price = '', category = '') {
            const phoneNumber = "992201482424";
            let message = "";
            if (sku && name) {
                message = `Здравствуйте! Меня заинтересовал товар с сайта "Королевские Жалюзи":%0A%0A` +
                         `🏷 *Артикул:* ${sku}%0A` +
                         `🪟 *Модель:* ${name}%0A` +
                         `📁 *Категория:* ${category || 'Жалюзи'}%0A` +
                         `💰 *Цена:* ${price || 'по запросу'}%0A%0A` +
                         `Пожалуйста, уточните наличие и условия заказа. Спасибо!`;
            } else {
                message = `Здравствуйте! Меня интересуют жалюзи с сайта "Королевские Жалюзи". Помогите с выбором?`;
            }
            const whatsappUrl = `https://wa.me/${phoneNumber}?text=${message}`;
            window.open(whatsappUrl, '_blank');
        }
        """,
        media_type="application/javascript"
    )

# ===== АВТОРИЗАЦИЯ =====
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

@app.post("/admin/login")
async def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if admin and admin.password_hash == hash_password(password):
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="admin_id", value=str(admin.id), httponly=True)
        return response
    return templates.TemplateResponse(
        "admin/login.html", 
        {"request": request, "error": "Неверный логин или пароль"}
    )

@app.get("/admin/logout")
async def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin_id")
    return response

# ===== ПУБЛИЧНЫЕ СТРАНИЦЫ =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    init_admin(db)
    popular_products = db.query(Product).filter(Product.is_popular == True).limit(6).all()
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "popular_products": popular_products,
            "categories": categories,
            "active_page": "home",
            "is_admin": check_admin_auth(request)
        }
    )

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "active_page": "about",
            "is_admin": check_admin_auth(request)
        }
    )

@app.get("/products", response_class=HTMLResponse)
async def products(
    request: Request,
    category: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category_id == category)
    products = query.all()
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "products": products,
            "categories": categories,
            "selected_category": category,
            "active_page": "products",
            "is_admin": check_admin_auth(request)
        }
    )

@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": "Товар не найден"},
            status_code=404
        )
    category = db.query(Category).filter(Category.id == product.category_id).first()
    related_products = db.query(Product).filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        "product_detail.html",
        {
            "request": request,
            "product": product,
            "category": category,
            "related_products": related_products,
            "categories": categories,
            "is_admin": check_admin_auth(request)
        }
    )

# ===== АДМИН ПАНЕЛЬ =====
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    products = db.query(Product).all()
    categories = db.query(Category).all()
    stats = {
        "total_products": len(products),
        "total_categories": len(categories),
        "in_stock": len([p for p in products if p.in_stock]),
        "popular": len([p for p in products if p.is_popular])
    }
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "products": products,
            "categories": categories,
            "stats": stats
        }
    )

# ===== УПРАВЛЕНИЕ ТОВАРАМИ =====
@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request, db: Session = Depends(get_db)):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    products = db.query(Product).all()
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "products": products,
            "categories": categories
        }
    )

@app.get("/admin/products/edit/{product_id}", response_class=HTMLResponse)
async def admin_edit_product_page(
    product_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return RedirectResponse(url="/admin/products?error=not_found", status_code=303)
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        "admin/edit_product.html",
        {
            "request": request,
            "product": product,
            "categories": categories
        }
    )

@app.post("/admin/products/add")
async def admin_add_product(
    request: Request,
    product_id: str = Form(...),
    name: str = Form(...),
    category_id: int = Form(...),
    description: str = Form(...),
    price: float = Form(None),
    material: str = Form(None),
    sizes: str = Form(None),
    in_stock: bool = Form(False),
    is_popular: bool = Form(False),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        existing_product = db.query(Product).filter(Product.product_id == product_id).first()
        if existing_product:
            return RedirectResponse(url="/admin/products?error=duplicate_id", status_code=303)
        image_path = None
        if image and image.filename:
            ext = image.filename.split(".")[-1]
            filename = f"product_{product_id}_{datetime.now().timestamp()}.{ext}"
            filepath = f"static/uploads/products/{filename}"
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_path = f"/static/uploads/products/{filename}"
        product = Product(
            product_id=product_id,
            name=name,
            category_id=category_id,
            description=description,
            price=price,
            material=material,
            sizes=sizes,
            in_stock=in_stock,
            is_popular=is_popular,
            image=image_path
        )
        db.add(product)
        db.commit()
        return RedirectResponse(url="/admin/products?added=1", status_code=303)
    except Exception as e:
        print(f"Error adding product: {e}")
        return RedirectResponse(url="/admin/products?error=add_failed", status_code=303)

@app.post("/admin/products/update/{product_id}")
async def admin_update_product(
    product_id: int,
    request: Request,
    product_id_code: str = Form(...),
    name: str = Form(...),
    category_id: int = Form(...),
    description: str = Form(...),
    price: float = Form(None),
    material: str = Form(None),
    sizes: str = Form(None),
    in_stock: bool = Form(False),
    is_popular: bool = Form(False),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.product_id = product_id_code
            product.name = name
            product.category_id = category_id
            product.description = description
            product.price = price if price else None
            product.material = material
            product.sizes = sizes
            product.in_stock = in_stock
            product.is_popular = is_popular
            if image and image.filename:
                if product.image:
                    try:
                        old_image_path = product.image[1:]
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except:
                        pass
                ext = image.filename.split(".")[-1]
                filename = f"product_{product_id_code}_{datetime.now().timestamp()}.{ext}"
                filepath = f"static/uploads/products/{filename}"
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(image.file, buffer)
                product.image = f"/static/uploads/products/{filename}"
            db.commit()
            return RedirectResponse(url="/admin/products?updated=1", status_code=303)
        else:
            return RedirectResponse(url="/admin/products?error=not_found", status_code=303)
    except Exception as e:
        print(f"Error updating product: {e}")
        return RedirectResponse(url="/admin/products?error=update_failed", status_code=303)

@app.post("/admin/products/delete/{product_id}")
async def admin_delete_product(
    product_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            if product.image:
                try:
                    os.remove(product.image[1:])
                except:
                    pass
            db.delete(product)
            db.commit()
        return RedirectResponse(url="/admin/products?deleted=1", status_code=303)
    except Exception as e:
        print(f"Error deleting product: {e}")
        return RedirectResponse(url="/admin/products?error=delete_failed", status_code=303)

@app.post("/admin/products/toggle-popular/{product_id}")
async def toggle_popular_product(
    product_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.is_popular = not product.is_popular
        db.commit()
    return RedirectResponse(url="/admin/products", status_code=303)

# ===== УПРАВЛЕНИЕ КАТЕГОРИЯМИ =====
@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request, db: Session = Depends(get_db)):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        "admin/categories.html",
        {
            "request": request,
            "categories": categories
        }
    )

@app.post("/admin/categories/add")
async def admin_add_category(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        image_path = None
        if image and image.filename:
            ext = image.filename.split(".")[-1]
            filename = f"category_{name}_{datetime.now().timestamp()}.{ext}"
            filepath = f"static/uploads/categories/{filename}"
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_path = f"/static/uploads/categories/{filename}"
        category = Category(
            name=name,
            description=description,
            image=image_path
        )
        db.add(category)
        db.commit()
        return RedirectResponse(url="/admin/categories?added=1", status_code=303)
    except Exception as e:
        print(f"Error adding category: {e}")
        return RedirectResponse(url="/admin/categories?error=add_failed", status_code=303)

@app.post("/admin/categories/update/{category_id}")
async def admin_update_category(
    category_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category:
            category.name = name
            category.description = description
            if image and image.filename:
                if category.image:
                    try:
                        old_image_path = category.image[1:]
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except:
                        pass
                ext = image.filename.split(".")[-1]
                filename = f"category_{name}_{datetime.now().timestamp()}.{ext}"
                filepath = f"static/uploads/categories/{filename}"
                with open(filepath, "wb") as buffer:
                    shutil.copyfileobj(image.file, buffer)
                category.image = f"/static/uploads/categories/{filename}"
            db.commit()
            return RedirectResponse(url="/admin/categories?updated=1", status_code=303)
        else:
            return RedirectResponse(url="/admin/categories?error=not_found", status_code=303)
    except Exception as e:
        print(f"Error updating category: {e}")
        return RedirectResponse(url="/admin/categories?error=update_failed", status_code=303)

@app.post("/admin/categories/delete/{category_id}")
async def admin_delete_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if category:
            if category.image:
                try:
                    image_path = category.image[1:]
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except:
                    pass
            db.delete(category)
            db.commit()
        return RedirectResponse(url="/admin/categories?deleted=1", status_code=303)
    except Exception as e:
        print(f"Error deleting category: {e}")
        return RedirectResponse(url="/admin/categories?error=delete_failed", status_code=303)

# ===== УПРАВЛЕНИЕ УСТАНОВЩИКАМИ =====
@app.get("/admin/installers", response_class=HTMLResponse)
async def admin_installers(request: Request, db: Session = Depends(get_db)):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    installers = db.query(Installer).all()
    return templates.TemplateResponse(
        "admin/installers.html",
        {
            "request": request,
            "installers": installers
        }
    )

@app.post("/admin/installers/add")
async def admin_add_installer(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    phone: str = Form(...),
    address: str = Form(None),
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        existing = db.query(Installer).filter(Installer.username == username).first()
        if existing:
            return RedirectResponse(url="/admin/installers?error=duplicate_username", status_code=303)
        installer = Installer(
            name=name,
            username=username,
            phone=phone,
            address=address if address else None
        )
        db.add(installer)
        db.commit()
        return RedirectResponse(url="/admin/installers?added=1", status_code=303)
    except Exception as e:
        print(f"Error adding installer: {e}")
        return RedirectResponse(url="/admin/installers?error=add_failed", status_code=303)

@app.post("/admin/installers/update/{installer_id}")
async def admin_update_installer(
    installer_id: int,
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    phone: str = Form(...),
    address: str = Form(None),
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        installer = db.query(Installer).filter(Installer.id == installer_id).first()
        if installer:
            existing = db.query(Installer).filter(
                Installer.username == username,
                Installer.id != installer_id
            ).first()
            if existing:
                return RedirectResponse(url="/admin/installers?error=duplicate_username", status_code=303)
            installer.name = name
            installer.username = username
            installer.phone = phone
            installer.address = address if address else None
            db.commit()
            return RedirectResponse(url="/admin/installers?updated=1", status_code=303)
        else:
            return RedirectResponse(url="/admin/installers?error=not_found", status_code=303)
    except Exception as e:
        print(f"Error updating installer: {e}")
        return RedirectResponse(url="/admin/installers?error=update_failed", status_code=303)

@app.post("/admin/installers/delete/{installer_id}")
async def admin_delete_installer(
    installer_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        installer = db.query(Installer).filter(Installer.id == installer_id).first()
        if installer:
            if installer.orders:
                return RedirectResponse(url="/admin/installers?error=has_orders", status_code=303)
            db.delete(installer)
            db.commit()
        return RedirectResponse(url="/admin/installers?deleted=1", status_code=303)
    except Exception as e:
        print(f"Error deleting installer: {e}")
        return RedirectResponse(url="/admin/installers?error=delete_failed", status_code=303)

@app.get("/admin/installers/{installer_id}/orders")
async def get_installer_orders(
    installer_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        installer = db.query(Installer).filter(Installer.id == installer_id).first()
        if not installer:
            return JSONResponse({"error": "Installer not found"}, status_code=404)
        orders = []
        for order in installer.orders:
            status_class = {
                "pending": "bg-yellow-500 bg-opacity-20 text-yellow-500",
                "production": "bg-blue-500 bg-opacity-20 text-blue-500",
                "ready": "bg-green-500 bg-opacity-20 text-green-500",
                "installed": "bg-purple-500 bg-opacity-20 text-purple-500",
                "cancelled": "bg-red-500 bg-opacity-20 text-red-500"
            }.get(order.status, "")
            status_text = {
                "pending": "🟡 Оформлен",
                "production": "🔵 На производстве",
                "ready": "🟢 Готов",
                "installed": "✅ Установлен",
                "cancelled": "❌ Отменен"
            }.get(order.status, order.status)
            orders.append({
                "id": order.id,
                "order_id": order.order_id,
                "client_name": order.client_name,
                "client_phone": order.client_phone,
                "total_sum": order.total_sum,
                "status": order.status,
                "status_class": status_class,
                "status_text": status_text,
                "payment_status": order.payment_status,
                "created_at": order.created_at.strftime("%d.%m.%Y")
            })
        return JSONResponse({"installer": installer.name, "orders": orders})
    except Exception as e:
        print(f"Error getting installer orders: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ===== УПРАВЛЕНИЕ ЗАКАЗАМИ =====

@app.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(request: Request, db: Session = Depends(get_db)):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    installers = db.query(Installer).all()
    return templates.TemplateResponse(
        "admin/orders.html",
        {
            "request": request,
            "orders": orders,
            "installers": installers
        }
    )

@app.post("/admin/orders/add")
async def admin_add_order(
    request: Request,
    client_name: str = Form(""),
    client_phone: str = Form(""),
    category_plisse: bool = Form(False),
    category_daynight: bool = Form(False),
    category_mini: bool = Form(False),
    plisse_items: str = Form("[]"),
    daynight_items: str = Form("[]"),
    mini_items: str = Form("[]"),
    total_sum: float = Form(0.0),
    installer_id: int = Form(None),
    installer_phone: str = Form(None),
    installer_username: str = Form(None),
    status: str = Form("pending"),
    payment_status: str = Form("unpaid"),
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Генерируем номер заказа
        last_order = db.query(Order).order_by(Order.id.desc()).first()
        if last_order and last_order.order_id:
            try:
                last_num = int(last_order.order_id.split("-")[-1])
                new_num = last_num + 1
            except:
                new_num = 1
        else:
            new_num = 1
        
        order_id = f"ORD-{datetime.now().year}-{new_num:04d}"
        
        # Создаем заказ
        order = Order(
            order_id=order_id,
            client_name=client_name or "Без имени",
            client_phone=client_phone or "Без телефона",
            category_plisse=category_plisse,
            category_daynight=category_daynight,
            category_mini=category_mini,
            plisse_items=plisse_items,
            daynight_items=daynight_items,
            mini_items=mini_items,
            total_sum=total_sum,
            installer_id=installer_id if installer_id else None,
            installer_phone=installer_phone,
            installer_username=installer_username,
            status=status,
            payment_status=payment_status
        )
        
        db.add(order)
        db.commit()
        print(f"✅ Заказ создан: {order_id}, сумма: {total_sum} TJS")
        print(f"📦 Плиссе: {plisse_items}")
        print(f"📦 День/Ночь: {daynight_items}")
        print(f"📦 Мини: {mini_items}")
        
        return RedirectResponse(url="/admin/orders?added=1", status_code=303)
        
    except Exception as e:
        print(f"❌ Error adding order: {e}")
        return RedirectResponse(url="/admin/orders?error=add_failed", status_code=303)

@app.post("/admin/orders/update/{order_id}")
async def admin_update_order(
    order_id: int,
    request: Request,
    client_name: str = Form(""),
    client_phone: str = Form(""),
    category_plisse: bool = Form(False),
    category_daynight: bool = Form(False),
    category_mini: bool = Form(False),
    plisse_items: str = Form("[]"),
    daynight_items: str = Form("[]"),
    mini_items: str = Form("[]"),
    total_sum: float = Form(0.0),
    installer_id: int = Form(None),
    installer_phone: str = Form(None),
    installer_username: str = Form(None),
    status: str = Form("pending"),
    payment_status: str = Form("unpaid"),
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.client_name = client_name or "Без имени"
            order.client_phone = client_phone or "Без телефона"
            order.category_plisse = category_plisse
            order.category_daynight = category_daynight
            order.category_mini = category_mini
            order.plisse_items = plisse_items
            order.daynight_items = daynight_items
            order.mini_items = mini_items
            order.total_sum = total_sum
            order.installer_id = installer_id if installer_id else None
            order.installer_phone = installer_phone
            order.installer_username = installer_username
            order.status = status
            order.payment_status = payment_status
            order.updated_at = datetime.now()
            
            db.commit()
            print(f"✅ Заказ обновлен: {order.order_id}, сумма: {total_sum} TJS")
            return RedirectResponse(url="/admin/orders?updated=1", status_code=303)
        else:
            return RedirectResponse(url="/admin/orders?error=not_found", status_code=303)
            
    except Exception as e:
        print(f"❌ Error updating order: {e}")
        return RedirectResponse(url="/admin/orders?error=update_failed", status_code=303)

@app.post("/admin/orders/delete/{order_id}")
async def admin_delete_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    if not check_admin_auth(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            db.delete(order)
            db.commit()
            print(f"✅ Заказ удален: {order.order_id}")
        return RedirectResponse(url="/admin/orders?deleted=1", status_code=303)
    except Exception as e:
        print(f"❌ Error deleting order: {e}")
        return RedirectResponse(url="/admin/orders?error=delete_failed", status_code=303)

# ===== ПОЛУЧЕНИЕ ДАННЫХ ЗАКАЗА ДЛЯ РЕДАКТИРОВАНИЯ =====
@app.get("/admin/orders/get/{order_id}")
async def get_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    if not check_admin_auth(request):
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=401)
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return JSONResponse({"success": False, "error": "Order not found"}, status_code=404)
        
        installer = None
        if order.installer_id:
            installer_obj = db.query(Installer).filter(Installer.id == order.installer_id).first()
            if installer_obj:
                installer = {
                    "id": installer_obj.id,
                    "name": installer_obj.name,
                    "username": installer_obj.username,
                    "phone": installer_obj.phone
                }
        
        return JSONResponse({
            "success": True,
            "order": {
                "id": order.id,
                "order_id": order.order_id,
                "client_name": order.client_name or "",
                "client_phone": order.client_phone or "",
                "category_plisse": order.category_plisse,
                "category_daynight": order.category_daynight,
                "category_mini": order.category_mini,
                "plisse_items": json.loads(order.plisse_items) if order.plisse_items else [],
                "daynight_items": json.loads(order.daynight_items) if order.daynight_items else [],
                "mini_items": json.loads(order.mini_items) if order.mini_items else [],
                "total_sum": order.total_sum or 0,
                "installer_id": order.installer_id,
                "installer_phone": order.installer_phone or "",
                "installer_username": order.installer_username or "",
                "installer": installer,
                "status": order.status or "pending",
                "payment_status": order.payment_status or "unpaid",
                "created_at": order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else ""
            }
        })
    except Exception as e:
        print(f"Error getting order: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

import os

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)