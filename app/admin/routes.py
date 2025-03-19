from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.admin import bp
from app.models import Package, GymMember, Staff, InventoryItem, Product, MemberAttendance, StaffAttendance, MemberPayment, Sale, SaleDetail
from app import db
from functools import wraps
from decimal import Decimal
from datetime import datetime, timedelta
import json
from sqlalchemy import text

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or 'admin' not in (current_user.privileges or []):
            flash('You do not have permission to access this page.')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get summary statistics
    total_members = GymMember.query.count()
    total_staff = Staff.query.count()
    total_packages = Package.query.count()
    
    # Get recent sales
    recent_sales = Sale.query.order_by(Sale.sale_timestamp.desc()).limit(5).all()
    
    # Get today's attendance
    today = datetime.utcnow().date()
    today_member_attendance = MemberAttendance.query.filter(
        db.func.date(MemberAttendance.check_in_time) == today
    ).count()
    
    # Get membership summary for current month
    membership_summary = db.session.execute(db.text('SELECT * FROM fn_membership_summary_current_month()')).fetchone()
    
    return render_template('admin/dashboard.html',
                           total_members=total_members,
                           total_staff=total_staff,
                           total_packages=total_packages,
                           recent_sales=recent_sales,
                           today_attendance=today_member_attendance,
                           membership_summary=membership_summary)

# Package Management
@bp.route('/packages')
@login_required
@admin_required
def packages():
    packages = Package.query.all()
    return render_template('admin/packages/list.html', packages=packages)

@bp.route('/packages/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_package():
    if request.method == 'POST':
        package = Package(
            package_name=request.form['package_name'],
            price=request.form['price'],
            duration_in_months=request.form['duration_in_months'],
            trainer_option=request.form['trainer_option'],
            cardio_access=bool(request.form.get('cardio_access')),
            sauna_access=int(request.form.get('sauna_access', 0)),
            steam_room_access=int(request.form.get('steam_room_access', 0)),
            timings=request.form['timings']
        )
        db.session.add(package)
        db.session.commit()
        flash('Package added successfully')
        return redirect(url_for('admin.packages'))
    return render_template('admin/packages/add.html')

@bp.route('/packages/edit/<int:package_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_package(package_id):
    package = Package.query.get_or_404(package_id)
    
    if request.method == 'POST':
        package.package_name = request.form['package_name']
        package.price = request.form['price']
        package.duration_in_months = request.form['duration_in_months']
        package.trainer_option = request.form['trainer_option']
        package.cardio_access = bool(request.form.get('cardio_access'))
        # Convert checkbox values to integers (1 if checked, 0 if unchecked)
        package.sauna_access = 1 if request.form.get('sauna_access') else 0
        package.steam_room_access = 1 if request.form.get('steam_room_access') else 0
        package.timings = request.form['timings']
        
        db.session.commit()
        flash('Package updated successfully')
        return redirect(url_for('admin.packages'))
    
    return render_template('admin/packages/edit.html', package=package)

@bp.route('/packages/delete/<int:package_id>', methods=['POST'])
@login_required
@admin_required
def delete_package(package_id):
    try:
        # First delete related package sales records
        db.session.execute(
            text('DELETE FROM package_sales WHERE package_id = :package_id'),
            {'package_id': package_id}
        )
        
        # Then delete the package
        package = Package.query.get_or_404(package_id)
        db.session.delete(package)
        db.session.commit()
        flash('Package deleted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting package. Please try again.', 'error')
        
    return redirect(url_for('admin.packages'))

# Member Management
@bp.route('/members')
@login_required
@admin_required
def members():
    # Use the database function to get member details including status
    members = db.session.execute(db.text('SELECT * FROM fn_get_all_member_details()')).fetchall()
    return render_template('admin/members/list.html', members=members)

@bp.route('/members/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_member():
    if request.method == 'POST':
        member = GymMember(
            full_name=request.form['full_name'],
            dob=datetime.strptime(request.form['dob'], '%Y-%m-%d'),
            phone_number=request.form['phone_number'],
            address=request.form['address'],
            package_id=request.form['package_id'],
            gender=request.form['gender'],
            medical_condition=request.form['medical_condition'],
            next_of_kin_name=request.form['next_of_kin_name'],
            next_of_kin_contact=request.form['next_of_kin_contact'],
            weight=request.form['weight'],
            height=request.form['height']
        )
        db.session.add(member)
        db.session.commit()
        flash('Member added successfully')
        return redirect(url_for('admin.members'))
    packages = Package.query.all()
    return render_template('admin/members/add.html', packages=packages)

@bp.route('/members/view/<int:member_id>')
@login_required
@admin_required
def view_member(member_id):
    member = GymMember.query.get_or_404(member_id)
    return render_template('admin/members/view.html', member=member)

@bp.route('/members/edit/<int:member_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_member(member_id):
    member = GymMember.query.get_or_404(member_id)
    
    if request.method == 'POST':
        member.full_name = request.form['full_name']
        member.dob = datetime.strptime(request.form['dob'], '%Y-%m-%d')
        member.phone_number = request.form['phone_number']
        member.address = request.form['address']
        member.package_id = request.form['package_id']
        member.gender = request.form['gender']
        member.medical_condition = request.form['medical_condition']
        member.next_of_kin_name = request.form['next_of_kin_name']
        member.next_of_kin_contact = request.form['next_of_kin_contact']
        member.weight = request.form['weight']
        member.height = request.form['height']
        
        db.session.commit()
        flash('Member updated successfully')
        return redirect(url_for('admin.members'))
    
    packages = Package.query.all()
    return render_template('admin/members/edit.html', member=member, packages=packages)

@bp.route('/members/delete/<int:member_id>', methods=['POST'])
@login_required
@admin_required
def delete_member(member_id):
    try:
        # First delete member attendance records
        db.session.execute(
            text('DELETE FROM member_attendance WHERE member_id = :member_id'),
            {'member_id': member_id}
        )
        
        # Then delete package sales records
        db.session.execute(
            text('DELETE FROM package_sales WHERE buying_member_id = :member_id'),
            {'member_id': member_id}
        )
        
        # Finally delete the member
        member = GymMember.query.get_or_404(member_id)
        db.session.delete(member)
        db.session.commit()
        flash('Member deleted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error deleting member. Please try again.', 'error')
        
    return redirect(url_for('admin.members'))

# Staff Management
@bp.route('/staff')
@login_required
@admin_required
def staff():
    staff = Staff.query.all()
    return render_template('admin/staff/list.html', staff=staff)

@bp.route('/staff/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_staff():
    if request.method == 'POST':
        try:
            # Check if username already exists
            existing_staff = Staff.query.filter_by(username=request.form['username']).first()
            if existing_staff:
                flash('Username already exists. Please choose a different username.', 'error')
                return render_template('admin/staff/add.html')

            # Get selected privileges and ensure they are properly formatted
            privileges = request.form.getlist('privileges')
            
            # Add admin privilege if staff type is manager
            if request.form['staff_type'] == 'manager' and 'admin' not in privileges:
                privileges.append('admin')

            new_staff = Staff(
                full_name=request.form['full_name'],
                staff_type=request.form['staff_type'],
                dob=datetime.strptime(request.form['dob'], '%Y-%m-%d').date(),
                phone_number=request.form['phone_number'],
                address=request.form['address'],
                gender=request.form['gender'],
                next_of_kin_name=request.form['next_of_kin_name'],
                next_of_kin_phone_number=request.form['next_of_kin_phone_number'],
                salary=Decimal(request.form['salary']),
                username=request.form['username'],
                privileges=privileges if privileges else None
            )
            new_staff.set_password(request.form['password'])
            
            db.session.add(new_staff)
            db.session.commit()
            flash('Staff member added successfully', 'success')
            return redirect(url_for('admin.staff'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding staff member. Please try again.', 'error')
            return render_template('admin/staff/add.html')
            
    return render_template('admin/staff/add.html')

@bp.route('/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_staff(staff_id):
    staff_member = Staff.query.get_or_404(staff_id)
    
    # Only allow admin to edit their own details
    if staff_member.privileges and 'admin' in staff_member.privileges and staff_member.staff_id != current_user.staff_id:
        flash('Only the admin can edit their own details', 'error')
        return redirect(url_for('admin.staff'))
    
    if request.method == 'POST':
        try:
            # Check if username exists and it's not the current staff member
            existing_staff = Staff.query.filter(Staff.username == request.form['username'], 
                                              Staff.staff_id != staff_id).first()
            if existing_staff:
                flash('Username already exists. Please choose a different username.', 'error')
                return render_template('admin/staff/edit.html', staff=staff_member)

            staff_member.full_name = request.form['full_name']
            staff_member.staff_type = request.form['staff_type']
            staff_member.dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
            staff_member.phone_number = request.form['phone_number']
            staff_member.address = request.form['address']
            staff_member.gender = request.form['gender']
            staff_member.next_of_kin_name = request.form['next_of_kin_name']
            staff_member.next_of_kin_phone_number = request.form['next_of_kin_phone_number']
            staff_member.salary = Decimal(request.form['salary'])
            staff_member.username = request.form['username']
            
            # Get selected privileges and ensure they are properly formatted
            privileges = request.form.getlist('privileges')
            
            # Add admin privilege if staff type is manager
            if request.form['staff_type'] == 'manager' and 'admin' not in privileges:
                privileges.append('admin')
            
            # Update privileges if not admin or if admin editing their own account
            if not ('admin' in staff_member.privileges) or staff_member.staff_id == current_user.staff_id:
                staff_member.privileges = privileges if privileges else None
            
            # Only update password if a new one is provided
            if request.form.get('password'):
                staff_member.set_password(request.form['password'])
                
            db.session.commit()
            flash('Staff member updated successfully', 'success')
            return redirect(url_for('admin.staff'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating staff member: {str(e)}', 'error')
            return render_template('admin/staff/edit.html', staff=staff_member)
        
    return render_template('admin/staff/edit.html', staff=staff_member)

# Inventory Management
@bp.route('/inventory')
@login_required
@admin_required
def inventory():
    items = db.session.execute(text('SELECT * FROM fn_render_current_items()')).fetchall()
    products = db.session.execute(text('SELECT * FROM fn_render_current_products()')).fetchall()
    product_status = db.session.execute(text('SELECT * FROM fn_get_product_inventory_status()')).fetchall()
    return render_template('admin/inventory.html', 
                         items=items, 
                         products=products,
                         product_status=product_status)

@bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_inventory():
    if request.method == 'POST':
        item = InventoryItem(
            item_name=request.form['item_name'],
            number_of_servings=request.form['number_of_servings'],
            cost_per_serving=request.form['cost_per_serving'],
            remaining_servings=request.form['number_of_servings'],
            other_charges=request.form.get('other_charges', 0)
        )
        db.session.add(item)
        db.session.commit()
        flash('Inventory item added successfully')
        return redirect(url_for('admin.inventory'))
    return render_template('admin/inventory/add.html')

# Keep this version of add_product and remove the other one
@bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        items = []
        for i in range(len(request.form.getlist('item_id[]'))):
            items.append({
                'item_id': request.form.getlist('item_id[]')[i],
                'servings_used': request.form.getlist('servings_used[]')[i]
            })
        
        db.session.execute(
            text('CALL sp_add_product(:name, :price, :description, :items)'),
            {
                'name': request.form['product_name'],
                'price': request.form['price'],
                'description': request.form['description'],
                'items': json.dumps(items)
            }
        )
        db.session.commit()
        flash('Product added successfully')
        return redirect(url_for('admin.inventory'))
    
    items = db.session.execute(text('SELECT * FROM fn_render_current_items()')).fetchall()
    return render_template('admin/products/add.html', items=items)

@bp.route('/inventory/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_inventory(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.item_name = request.form['item_name']
        item.number_of_servings = request.form['number_of_servings']
        item.cost_per_serving = request.form['cost_per_serving']
        item.remaining_servings = request.form['remaining_servings']
        item.other_charges = request.form.get('other_charges', 0)
        
        db.session.commit()
        flash('Inventory item updated successfully')
        return redirect(url_for('admin.inventory'))
        
    return render_template('admin/inventory/edit.html', item=item)

@bp.route('/inventory/delete/<int:item_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_inventory(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Inventory item deleted successfully')
    return redirect(url_for('admin.inventory'))

# Sales Management
@bp.route('/membership')
@login_required
@admin_required
def membership():
    members = GymMember.query.all()
    packages = Package.query.all()
    
    # Get package sales history using the function
    result = db.session.execute(text('SELECT * FROM fn_view_package_sales()'))
    package_sales = result.fetchall()
    
    return render_template('admin/membership.html',
                           members=members,
                           packages=packages,
                           package_sales=package_sales)

@bp.route('/purchase_package', methods=['POST'])
@login_required
@admin_required
def purchase_package():
    member_id = request.form.get('member_id')
    package_id = request.form.get('package_id')
    
    if not member_id or not package_id:
        flash('Please select both member and package.')
        return redirect(url_for('admin.membership'))
    
    try:
        # Call the stored procedure to record the package sale
        db.session.execute(
            text('CALL sp_purchase_package(:package_id, :member_id, :staff_id)'),
            {
                'package_id': package_id,
                'member_id': member_id,
                'staff_id': current_user.staff_id
            }
        )
        db.session.commit()
        flash('Package purchased successfully!')
    except Exception as e:
        db.session.rollback()
        flash(f'Error purchasing package: {str(e)}')
    
    return redirect(url_for('admin.membership'))

@bp.route('/sales')
@login_required
@admin_required
def sales():
    # Get all sales details using the database function
    sales = db.session.execute(text('SELECT * FROM fn_get_all_sales()')).fetchall()
    return render_template('admin/sales/list.html', sales=sales)

@bp.route('/sales/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_sale():
    if request.method == 'GET':
        products = db.session.execute(text('''
            SELECT p.*, CASE WHEN fn_check_product_availability(p.product_id, 1) 
            THEN true ELSE false END as available 
            FROM products p
        ''')).fetchall()
        items = db.session.execute(text('''
            SELECT * FROM inventory_items 
            WHERE remaining_servings > 0
        ''')).fetchall()
        return render_template('admin/sales/add.html', products=products, items=items)

    try:
        data = request.get_json()
        sale_lines = []
        
        for item in data['items']:
            item_type = item['item_type']
            item_id = int(item['item_id'])
            quantity = int(item['quantity'])
            unit_price = float(item['unit_price'])
            
            # Format each line for the sale_line array
            if item_type == 'product':
                sale_lines.append(f"ROW('product', {item_id}, NULL, {quantity}, {unit_price})")
            else:
                sale_lines.append(f"ROW('item', NULL, {item_id}, {quantity}, {unit_price})")
        
        # Execute the sale recording function
        result = db.session.execute(
            text(f"""
                SELECT sp_record_sale(
                    :payment_method,
                    :staff_id,
                    ARRAY[{','.join(sale_lines)}]::sale_line[]
                )
            """),
            {
                'payment_method': data['payment_method'],
                'staff_id': current_user.staff_id
            }
        )
        
        sale_id = result.scalar()
        db.session.commit()
        
        # Get sale details for receipt
        sale = Sale.query.get(sale_id)
        receipt_html = sale.generate_receipt()
        
        return jsonify({
            'success': True,
            'sale_id': sale_id,
            'receipt': receipt_html,
            'message': 'Sale recorded successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing sale: {str(e)}'
        }), 500

@bp.route('/sales/view/<int:sale_id>')
@login_required
@admin_required
def view_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template('admin/sales/view.html', sale=sale)

@bp.route('/sales/receipt/<int:sale_id>')
@login_required
def print_receipt(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    receipt = sale.generate_receipt()
    return render_template('admin/sales/receipt.html', receipt=receipt)

# Reports
@bp.route('/reports/attendance')
@login_required
@admin_required
def attendance_report():
    start_date = request.args.get('start_date', datetime.utcnow().date())
    end_date = request.args.get('end_date', datetime.utcnow().date())
    
    member_attendance = MemberAttendance.query.filter(
        db.func.date(MemberAttendance.check_in_time).between(start_date, end_date)
    ).all()
    
    staff_attendance = StaffAttendance.query.filter(
        db.func.date(StaffAttendance.check_in_time).between(start_date, end_date)
    ).all()
    
    return render_template('admin/reports/attendance.html',
                           member_attendance=member_attendance,
                           staff_attendance=staff_attendance)

@bp.route('/reports/sales')
@login_required
@admin_required
def sales_report():
    start_date = request.args.get('start_date', datetime.utcnow().date())
    end_date = request.args.get('end_date', datetime.utcnow().date())
    
    sales = Sale.query.filter(
        db.func.date(Sale.sale_timestamp).between(start_date, end_date)
    ).all()
    
    # Calculate total sales and group by payment method
    total_sales = sum(sale.total_amount for sale in sales)
    sales_by_method = {}
    for sale in sales:
        sales_by_method[sale.payment_method] = sales_by_method.get(sale.payment_method, 0) + float(sale.total_amount)
    
    return render_template('admin/reports/sales.html',
                           sales=sales,
                           total_sales=total_sales,
                           sales_by_method=sales_by_method)

@bp.route('/reports/expenses')
@login_required
@admin_required
def expense_report():
    start_date = request.args.get('start_date', datetime.utcnow().date())
    end_date = request.args.get('end_date', datetime.utcnow().date())
    
    # Calculate inventory expenses
    inventory_expenses = db.session.query(
        db.func.sum(InventoryItem.cost_per_serving * InventoryItem.number_of_servings + InventoryItem.other_charges)
    ).filter(db.func.date(InventoryItem.date_added).between(start_date, end_date)).scalar() or 0
    
    # Calculate salary expenses
    salary_expenses = db.session.query(db.func.sum(Staff.salary)).scalar() or 0
    
    total_expenses = float(inventory_expenses) + float(salary_expenses)
    
    return render_template('admin/reports/expenses.html',
                           inventory_expenses=inventory_expenses,
                           salary_expenses=salary_expenses,
                           total_expenses=total_expenses)

@bp.route('/api/chart-data')
@login_required
@admin_required
def chart_data():
    # Get attendance data for the last 7 days
    dates = [(datetime.utcnow() - timedelta(days=i)).date() for i in range(7)]
    attendance_data = []
    for date in dates:
        count = MemberAttendance.query.filter(
            db.func.date(MemberAttendance.check_in_time) == date
        ).count()
        attendance_data.append({'date': date.strftime('%Y-%m-%d'), 'count': count})
    
    # Get sales data for the last 7 days
    sales_data = []
    for date in dates:
        total = db.session.query(db.func.sum(Sale.total_amount)).filter(
            db.func.date(Sale.sale_timestamp) == date
        ).scalar() or 0
        sales_data.append({'date': date.strftime('%Y-%m-%d'), 'total': float(total)})
    
    return jsonify({
        'attendance': attendance_data,
        'sales': sales_data
    })

from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import text
from flask_login import login_required, current_user
from app.admin import bp as admin
from app import db

@admin.route('/attendance', methods=['GET', 'POST'])
@login_required
@admin_required
def attendance():
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        action = request.form.get('action')
        current_time = datetime.now()

        try:
            if action == 'check_in':
                # Check if member already has an active check-in
                result = db.session.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM member_attendance 
                        WHERE member_id = :member_id 
                        AND DATE(check_in_time) = CURRENT_DATE 
                        AND check_out_time IS NULL
                    """),
                    {'member_id': member_id}
                ).scalar()

                if result > 0:
                    flash('Member already has an active check-in today!', 'error')
                else:
                    db.session.execute(
                        text('CALL sp_mark_member_attendance(:member_id, :check_in, :check_out, :staff_id)'),
                        {
                            'member_id': member_id,
                            'check_in': current_time,
                            'check_out': None,
                            'staff_id': current_user.staff_id
                        }
                    )
                    db.session.commit()
                    flash('Check-in marked successfully!', 'success')

            elif action == 'check_out':
                db.session.execute(
                    text('CALL sp_mark_member_attendance(:member_id, :check_in, :check_out, :staff_id)'),
                    {
                        'member_id': member_id,
                        'check_in': current_time,
                        'check_out': current_time,
                        'staff_id': current_user.staff_id
                    }
                )
                db.session.commit()
                flash('Check-out marked successfully!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(str(e), 'error')

        return redirect(url_for('admin.attendance'))

    # Get all attendance records and members
    attendance_records = db.session.execute(
        text('SELECT * FROM fn_get_all_member_attendance() ORDER BY check_in_time DESC')
    ).fetchall()
    members = db.session.execute(
        text('SELECT member_id, full_name FROM gym_members ORDER BY full_name')
    ).fetchall()

    return render_template('admin/attendance.html',
                         attendance_records=attendance_records,
                         members=members)


# @bp.route('/products/add', methods=['GET', 'POST'])
# @login_required
# @admin_required
# def add_product():
#     if request.method == 'POST':
#         db.session.execute(
#             text('CALL sp_add_product(:name, :price)'),
#             {
#                 'name': request.form['product_name'],
#                 'price': request.form['price']
#             }
#         )
#         db.session.commit()
#         flash('Product added successfully')
#         return redirect(url_for('admin.inventory'))
#     return render_template('admin/products/add.html')

@bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.product_name = request.form['product_name']
        product.price = request.form['price']
        
        db.session.commit()
        flash('Product updated successfully')
        return redirect(url_for('admin.inventory'))
        
    return render_template('admin/products/edit.html', product=product)

@bp.route('/products/delete/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully')
    return redirect(url_for('admin.inventory'))

@bp.route('/staff/delete/<int:staff_id>')
@login_required
@admin_required
def delete_staff(staff_id):
    if staff_id == current_user.staff_id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.staff'))
        
    staff_member = Staff.query.get_or_404(staff_id)
    
    try:
        db.session.delete(staff_member)
        db.session.commit()
        flash('Staff member deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting staff member. They may have associated records.', 'error')
        
    return redirect(url_for('admin.staff'))

@admin.route('/staff/attendance')
@login_required
def staff_attendance():
    # Get all staff for dropdown
    staff_list = Staff.query.order_by(Staff.full_name).all()
    
    # Get attendance records using SQLAlchemy
    attendance_records = db.session.execute(text("SELECT * FROM fn_get_all_staff_attendance()")).fetchall()
    
    return render_template('admin/staff/attendance.html', 
                         staff_list=staff_list,
                         attendance_records=attendance_records,
                         timedelta=timedelta)

@admin.route('/staff/mark-attendance', methods=['POST'])
@login_required
def mark_staff_attendance():
    data = request.get_json()
    staff_id = data.get('staff_id')
    action = data.get('action')
    
    try:
        if action == 'check_in':
            db.session.execute(text("""
                CALL sp_mark_staff_attendance(
                    CAST(:staff_id AS INTEGER), 
                    CAST(NOW() AS TIMESTAMP), 
                    NULL, 
                    CAST(:marked_by AS INTEGER)
                )
            """), {'staff_id': staff_id, 'marked_by': current_user.staff_id})
        else:  # check_out
            db.session.execute(text("""
                CALL sp_mark_staff_attendance(
                    CAST(:staff_id AS INTEGER), 
                    CAST(CURRENT_DATE AS TIMESTAMP), 
                    CAST(NOW() AS TIMESTAMP), 
                    CAST(:marked_by AS INTEGER)
                )
            """), {'staff_id': staff_id, 'marked_by': current_user.staff_id})
            
        db.session.commit()
        return jsonify({'success': True})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400