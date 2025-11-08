from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from threading import Lock
import os
import time
from dotenv import load_dotenv
from decimal import Decimal

# Load environment variables from .env file if available
load_dotenv()

app = Flask(__name__)

# Secret key for flashing messages in the simple UI
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')

@app.route('/health')
def health_check():
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# --- Database Configuration ---
db_user = os.environ.get('DB_USER', 'inventory_user')
db_password = os.environ.get('DB_PASSWORD', 'inventory_pass')
db_host = os.environ.get('DB_HOST', '127.0.0.1')  # Change if needed
db_name = os.environ.get('DB_NAME', 'inventory_db')

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
order_lock = Lock()

# --- Database Models ---
class Product(db.Model):
    __tablename__ = 'Products'
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    __tablename__ = 'Orders'
    order_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(50), nullable=False)
    items = db.relationship('OrderItem', backref='order', cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'Order_Items'
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('Orders.order_id'))
    product_id = db.Column(db.Integer, db.ForeignKey('Products.product_id'))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

# --- Routes ---

@app.route('/')
def index():
    # Render a simple HTML index page if templates are available
    try:
        return render_template('index.html')
    except Exception:
        return "Hello, Inventory Management System!"

@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400
    try:
        product = Product(
            name=data.get('name'),
            description=data.get('description', ''),
            price=data.get('price'),
            stock_quantity=data.get('stock_quantity')
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({"message": "Product added", "product_id": product.product_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid input"}), 400
    customer_id = data.get('customer_id')
    items = data.get('items')  # Expected to be a list of {"product_id": ..., "quantity": ...}
    if not customer_id or not items:
        return jsonify({"error": "Missing customer_id or items"}), 400
    with order_lock:
        try:
            order = Order(customer_id=customer_id, status="Processing")
            db.session.add(order)
            db.session.flush()  # Ensure order_id is available

            for item in items:
                product_id = item.get('product_id')
                quantity = item.get('quantity')
                product = Product.query.filter_by(product_id=product_id).with_for_update().first()
                if product and product.stock_quantity >= quantity:
                    product.stock_quantity -= quantity
                    order_item = OrderItem(
                        order_id=order.order_id,
                        product_id=product_id,
                        quantity=quantity,
                        price=product.price
                    )
                    db.session.add(order_item)
                else:
                    db.session.rollback()
                    return jsonify({"error": f"Insufficient stock for product {product_id}"}), 400

            order.status = "Completed"
            db.session.commit()
            return jsonify({"message": "Order placed", "order_id": order.order_id}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
#hi this is a commit
@app.route('/report', methods=['GET'])
def report():
    try:
        products = Product.query.all()
        orders = Order.query.all()
        product_list = [
            {"product_id": p.product_id, "name": p.name, "stock_quantity": p.stock_quantity}
            for p in products
        ]
        order_list = [
            {"order_id": o.order_id, "customer_id": o.customer_id, "status": o.status, "order_date": o.order_date}
            for o in orders
        ]
        return jsonify({"products": product_list, "orders": order_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Simple HTML UI routes ---
@app.route('/ui')
def ui_index():
    return redirect(url_for('index'))


@app.route('/ui/add_product', methods=['GET', 'POST'])
def ui_add_product():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        description = request.form.get('description', '')
        price = request.form.get('price')
        stock_quantity = request.form.get('stock_quantity')
        try:
            product = Product(
                name=name,
                description=description,
                price=price,
                stock_quantity=stock_quantity
            )
            db.session.add(product)
            db.session.commit()
            flash('Product added successfully', 'success')
            return redirect(url_for('ui_report'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {e}', 'danger')
            return redirect(url_for('ui_add_product'))
    return render_template('add_product.html')


@app.route('/ui/report')
def ui_report():
    try:
        products = Product.query.all()
        orders = Order.query.all()
        return render_template('report.html', products=products, orders=orders)
    except Exception as e:
        flash(f'Error loading report: {e}', 'danger')
        return render_template('report.html', products=[], orders=[])


@app.route('/ui/edit_product/<int:product_id>', methods=['GET', 'POST'])
def ui_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        price = request.form.get('price')
        stock_quantity = request.form.get('stock_quantity')
        try:
            product.name = name
            product.description = description
            # convert types
            if price is not None:
                product.price = Decimal(price)
            if stock_quantity is not None:
                product.stock_quantity = int(stock_quantity)
            db.session.commit()
            flash('Product updated successfully', 'success')
            return redirect(url_for('ui_report'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {e}', 'danger')
            return redirect(url_for('ui_edit_product', product_id=product_id))
    return render_template('edit_product.html', product=product)


@app.route('/ui/delete_product/<int:product_id>', methods=['POST'])
def ui_delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found', 'warning')
        return redirect(url_for('ui_report'))
    try:
        # Prevent deleting a product that appears in any order items
        from sqlalchemy import exists
        linked = db.session.query(exists().where(OrderItem.product_id == product_id)).scalar()
        if linked:
            flash('Cannot delete product: it is referenced by existing orders', 'warning')
        else:
            db.session.delete(product)
            db.session.commit()
            flash('Product deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {e}', 'danger')
    return redirect(url_for('ui_report'))


@app.route('/ui/place_order', methods=['GET', 'POST'])
def ui_place_order():
    if request.method == 'POST':
        # Form will submit customer_id and quantities for products
        try:
            customer_id = request.form.get('customer_id') or 0
            # collect items: form fields named qty_<product_id>
            items = []
            for p in Product.query.all():
                q = request.form.get(f'qty_{p.product_id}')
                if q:
                    try:
                        qty = int(q)
                    except ValueError:
                        qty = 0
                    if qty > 0:
                        items.append({'product_id': p.product_id, 'quantity': qty})

            if not items:
                flash('No items selected for the order', 'warning')
                return redirect(url_for('ui_place_order'))

            # Reuse place_order logic but implement inline to return flashes
            with order_lock:
                order = Order(customer_id=int(customer_id), status='Processing')
                db.session.add(order)
                db.session.flush()
                for item in items:
                    product = Product.query.filter_by(product_id=item['product_id']).with_for_update().first()
                    if product and product.stock_quantity >= item['quantity']:
                        product.stock_quantity -= item['quantity']
                        order_item = OrderItem(
                            order_id=order.order_id,
                            product_id=product.product_id,
                            quantity=item['quantity'],
                            price=product.price
                        )
                        db.session.add(order_item)
                    else:
                        db.session.rollback()
                        flash(f'Insufficient stock for product {item["product_id"]}', 'danger')
                        return redirect(url_for('ui_place_order'))
                order.status = 'Completed'
                db.session.commit()
                flash(f'Order placed successfully (order id: {order.order_id})', 'success')
                return redirect(url_for('ui_report'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error placing order: {e}', 'danger')
            return redirect(url_for('ui_place_order'))

    products = Product.query.all()
    return render_template('place_order.html', products=products)

def wait_for_mysql(max_retries=30, delay=2):
    """Wait for MySQL to be ready before starting the app."""
    import pymysql
    for i in range(max_retries):
        try:
            # Try to connect to MySQL with the database
            # MySQL container creates the database automatically via MYSQL_DATABASE env var
            connection = pymysql.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name,
                connect_timeout=5
            )
            connection.close()
            print("MySQL is ready!")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"Waiting for MySQL... (attempt {i+1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"Warning: Could not connect to MySQL after {max_retries} retries: {e}")
                print("Continuing anyway - database tables will be created when connection is available")
    return False

if __name__ == '__main__':
    # Wait for MySQL to be ready (useful in Docker/Kubernetes)
    wait_for_mysql()
    
    # Create database tables if they don't exist
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created/verified successfully!")
        except Exception as e:
            print(f"Error creating tables: {e}")
    
    app.run(host="0.0.0.0", port=5000, debug=True)
