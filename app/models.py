from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(id):
    return Staff.query.get(int(id))

class Staff(UserMixin, db.Model):
    __tablename__ = 'staff'
    staff_id = db.Column('staff_id', db.Integer, primary_key=True)
    full_name = db.Column('full_name', db.String(100), nullable=False)
    staff_type = db.Column('staff_type', db.String(50))
    dob = db.Column('dob', db.Date)
    phone_number = db.Column('phone_number', db.String(15))
    address = db.Column('address', db.Text)
    gender = db.Column('gender', db.String(10))
    next_of_kin_name = db.Column('next_of_kin_name', db.String(100))
    next_of_kin_phone_number = db.Column('next_of_kin_phone_number', db.String(15))
    salary = db.Column('salary', db.Numeric(10, 2))
    privileges = db.Column('privileges', db.ARRAY(db.Text))
    username = db.Column('username', db.String(50), unique=True, nullable=False)
    password = db.Column('password', db.String(255), nullable=False)

    def get_id(self):
        return str(self.staff_id)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def has_privilege(self, privilege):
        return privilege in (self.privileges or [])

class Package(db.Model):
    __tablename__ = 'packages'
    package_id = db.Column('package_id', db.Integer, primary_key=True)
    package_name = db.Column('package_name', db.String(100), nullable=False)
    price = db.Column('price', db.Numeric(10, 2), nullable=False)
    duration_in_months = db.Column('duration_in_months', db.Integer, nullable=False)
    trainer_option = db.Column('trainer_option', db.String(50), nullable=False)
    cardio_access = db.Column('cardio_access', db.Boolean, nullable=False, default=False)
    sauna_access = db.Column('sauna_access', db.SmallInteger, nullable=False, default=0)
    steam_room_access = db.Column('steam_room_access', db.SmallInteger, nullable=False, default=0)
    timings = db.Column('timings', db.String(50), nullable=False)

class GymMember(db.Model):
    __tablename__ = 'gym_members'
    member_id = db.Column('member_id', db.Integer, primary_key=True)
    full_name = db.Column('full_name', db.String(100), nullable=False)
    dob = db.Column('dob', db.Date, nullable=False)
    phone_number = db.Column('phone_number', db.String(15))
    address = db.Column('address', db.Text)
    package_id = db.Column('package_id', db.Integer, db.ForeignKey('packages.package_id'))
    gender = db.Column('gender', db.String(10))
    medical_condition = db.Column('medical_condition', db.Text)
    next_of_kin_name = db.Column('next_of_kin_name', db.String(100))
    next_of_kin_contact = db.Column('next_of_kin_contact', db.String(15))
    weight = db.Column('weight', db.Numeric(5, 2))
    height = db.Column('height', db.Numeric(5, 2))
    joining_date = db.Column('joining_date', db.Date, nullable=False, default=datetime.utcnow)

class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'
    item_id = db.Column('item_id', db.Integer, primary_key=True)
    item_name = db.Column('item_name', db.String(100), nullable=False)
    number_of_servings = db.Column('number_of_servings', db.Integer, nullable=False)
    cost_per_serving = db.Column('cost_per_serving', db.Numeric(10, 2))
    remaining_servings = db.Column('remaining_servings', db.Integer, nullable=False)
    other_charges = db.Column('other_charges', db.Numeric(10, 2))
    date_added = db.Column('date_added', db.Date, nullable=False, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column('product_id', db.Integer, primary_key=True)
    product_name = db.Column('product_name', db.String(100), nullable=False)
    price = db.Column('price', db.Numeric(10, 2), nullable=False)

class ProductItem(db.Model):
    __tablename__ = 'product_items'
    product_id = db.Column('product_id', db.Integer, db.ForeignKey('products.product_id'), primary_key=True)
    item_id = db.Column('item_id', db.Integer, db.ForeignKey('inventory_items.item_id'), primary_key=True)
    servings_used = db.Column('servings_used', db.Integer, nullable=False)

class MemberAttendance(db.Model):
    __tablename__ = 'member_attendance'
    attendance_id = db.Column('attendance_id', db.Integer, primary_key=True)
    member_id = db.Column('member_id', db.Integer, db.ForeignKey('gym_members.member_id'), nullable=False)
    check_in_time = db.Column('check_in_time', db.DateTime, nullable=False)
    check_out_time = db.Column('check_out_time', db.DateTime)
    marked_by_staff_id = db.Column('marked_by_staff_id', db.Integer, db.ForeignKey('staff.staff_id'))

class StaffAttendance(db.Model):
    __tablename__ = 'staff_attendance'
    staff_attendance_id = db.Column('staff_attendance_id', db.Integer, primary_key=True)
    staff_id = db.Column('staff_id', db.Integer, db.ForeignKey('staff.staff_id'), nullable=False)
    check_in_time = db.Column('check_in_time', db.DateTime, nullable=False)
    check_out_time = db.Column('check_out_time', db.DateTime)
    marked_by_staff_id = db.Column('marked_by_staff_id', db.Integer, db.ForeignKey('staff.staff_id'))

class MemberPayment(db.Model):
    __tablename__ = 'member_payments'
    payment_id = db.Column('payment_id', db.Integer, primary_key=True)
    payment_date = db.Column('payment_date', db.DateTime, nullable=False, default=datetime.utcnow)
    member_id = db.Column('member_id', db.Integer, db.ForeignKey('gym_members.member_id'), nullable=False)
    package_id = db.Column('package_id', db.Integer, db.ForeignKey('packages.package_id'))
    amount = db.Column('amount', db.Numeric(10, 2), nullable=False)
    received_by_staff_id = db.Column('received_by_staff_id', db.Integer, db.ForeignKey('staff.staff_id'))

class Sale(db.Model):
    __tablename__ = 'sales'
    sale_id = db.Column(db.Integer, primary_key=True)
    sale_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    received_by_staff_id = db.Column(db.Integer, db.ForeignKey('staff.staff_id'))
    
    # Correct relationship setup
    received_by = db.relationship('Staff', backref='sales_received', foreign_keys=[received_by_staff_id])
    sale_details = db.relationship('SaleDetail', backref='sale', lazy=True)

    def generate_receipt(self):
        receipt = f"""
        <div class="text-center mb-4">
            <h2 class="text-xl font-bold">GYM FITNESS</h2>
            <p class="text-sm">Receipt #{self.sale_id}</p>
            <p class="text-sm">{self.pakistan_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="border-t border-b py-2 mb-4">
            <table class="w-full">
                <thead>
                    <tr>
                        <th class="text-left">Item</th>
                        <th class="text-right">Qty</th>
                        <th class="text-right">Price</th>
                        <th class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for detail in self.sale_details:
            name = detail.product.product_name if detail.product_id else detail.item.item_name
            receipt += f"""
                    <tr>
                        <td>{name}</td>
                        <td class="text-right">{detail.quantity}</td>
                        <td class="text-right">${detail.price:.2f}</td>
                        <td class="text-right">${(detail.quantity * detail.price):.2f}</td>
                    </tr>
            """
            
        receipt += f"""
                </tbody>
            </table>
        </div>
        <div class="flex justify-between font-bold">
            <span>Total:</span>
            <span>${self.total_amount:.2f}</span>
        </div>
        <div class="mt-4 text-sm">
            <p>Payment Method: {self.payment_method}</p>
            <p>Staff: {self.received_by.full_name}</p>
        </div>
        """
        return receipt

    @property
    def pakistan_time(self):
        """Convert UTC time to Pakistan time (UTC+5)"""
        return self.sale_timestamp + timedelta(hours=5)

class SaleDetail(db.Model):
    __tablename__ = 'sale_details'
    sale_detail_id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.sale_id'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'))
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.item_id'))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    
    product = db.relationship('Product')
    item = db.relationship('InventoryItem')