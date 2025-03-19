from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.staff import bp
from app.models import Package, GymMember, Staff, InventoryItem, Product, MemberAttendance, Sale, SaleDetail
from app import db
from sqlalchemy import text
from functools import wraps
from datetime import datetime

def check_privilege(privilege):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_privilege(privilege):
                flash('You do not have permission to access this page.')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/dashboard')
@login_required
def dashboard():
    # Get today's statistics based on staff privileges
    today = datetime.utcnow().date()
    
    # Initialize counters
    today_attendance = 0
    today_sales = 0
    recent_activities = []
    
    # Check attendance privileges
    if current_user.has_privilege('view_attendance'):
        today_attendance = MemberAttendance.query.filter(
            db.func.date(MemberAttendance.check_in_time) == today
        ).count()
        
    # Check sales privileges
    if current_user.has_privilege('view_sales'):
        sales = Sale.query.filter(
            db.func.date(Sale.sale_timestamp) == today
        ).all()
        today_sales = sum(sale.total_amount for sale in sales)
        
        # Get recent sales for activity feed
        recent_sales = Sale.query.order_by(Sale.sale_timestamp.desc()).limit(5).all()
        for sale in recent_sales:
            recent_activities.append({
                'type': 'sale',
                'timestamp': sale.sale_timestamp,
                'details': f'Sale #{sale.sale_id} - ${float(sale.total_amount)}'
            })
    
    return render_template('staff/dashboard.html',
                           today_attendance=today_attendance,
                           today_sales=today_sales,
                           recent_activities=recent_activities)

# Member Management (Limited)
@bp.route('/members')
@login_required
@check_privilege('view_members')
def members():
    members = GymMember.query.all()
    return render_template('staff/members/list.html', members=members)

@bp.route('/members/attendance', methods=['POST'])
@login_required
@check_privilege('record_attendance')
def record_member_attendance():
    member_id = request.form.get('member_id')
    action = request.form.get('action')  # 'check_in' or 'check_out'
    
    member = GymMember.query.get_or_404(member_id)
    
    if action == 'check_in':
        attendance = MemberAttendance(
            member_id=member_id,
            check_in_time=datetime.utcnow(),
            marked_by_staff_id=current_user.staff_id
        )
        db.session.add(attendance)
        flash('Member checked in successfully')
    
    elif action == 'check_out':
        attendance = MemberAttendance.query.filter_by(
            member_id=member_id,
            check_out_time=None
        ).first()
        if attendance:
            attendance.check_out_time = datetime.utcnow()
            flash('Member checked out successfully')
        else:
            flash('No active check-in found for this member')
    
    db.session.commit()
    return redirect(url_for('staff.members'))

# Inventory Management (Limited)
@bp.route('/inventory')
@login_required
@check_privilege('view_inventory')
def inventory():
    items = InventoryItem.query.all()
    return render_template('staff/inventory/list.html', items=items)

# Sales Management
@bp.route('/membership')
@login_required
def membership():
    if not current_user.has_privilege('view_membership'):
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    members = GymMember.query.all()
    packages = Package.query.all()
    
    # Get package sales history using the function
    result = db.session.execute(text('SELECT * FROM fn_view_package_sales()'))
    package_sales = result.fetchall()
    
    return render_template('staff/membership.html',
                           members=members,
                           packages=packages,
                           package_sales=package_sales)

@bp.route('/purchase_package', methods=['POST'])
@login_required
def purchase_package():
    if not current_user.has_privilege('sell_packages'):
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
    member_id = request.form.get('member_id')
    package_id = request.form.get('package_id')
    
    if not member_id or not package_id:
        flash('Please select both member and package.')
        return redirect(url_for('staff.membership'))
    
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
    
    return redirect(url_for('staff.membership'))

@bp.route('/sales')
@login_required
@check_privilege('view_sales')
def sales():
    sales = Sale.query.order_by(Sale.sale_timestamp.desc()).all()
    return render_template('staff/sales/list.html', sales=sales)

@bp.route('/sales/add', methods=['GET', 'POST'])
@login_required
@check_privilege('make_sales')
def add_sale():
    if request.method == 'POST':
        data = request.get_json()
        
        sale = Sale(
            total_amount=data['total_amount'],
            payment_method=data['payment_method'],
            received_by_staff_id=current_user.staff_id
        )
        db.session.add(sale)
        db.session.flush()
        
        for item in data['items']:
            sale_detail = SaleDetail(
                sale_id=sale.sale_id,
                item_type=item['type'],
                product_id=item.get('product_id'),
                item_id=item.get('item_id'),
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(sale_detail)
        
        db.session.commit()
        return jsonify({'success': True, 'sale_id': sale.sale_id})
    
    products = Product.query.all()
    items = InventoryItem.query.all()
    return render_template('staff/sales/add.html', products=products, items=items)

# Profile Management
@bp.route('/profile')
@login_required
def profile():
    return render_template('staff/profile.html')

@bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect')
        return redirect(url_for('staff.profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    flash('Password updated successfully')
    return redirect(url_for('staff.profile'))

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        try:
            current_user.full_name = request.form['full_name']
            current_user.phone_number = request.form['phone_number']
            current_user.address = request.form['address']
            current_user.next_of_kin_name = request.form['next_of_kin_name']
            current_user.next_of_kin_phone_number = request.form['next_of_kin_phone_number']
            
            # Only update password if provided
            if request.form.get('password'):
                current_user.set_password(request.form['password'])
                
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('staff.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
            
    return render_template('staff/edit_profile.html')