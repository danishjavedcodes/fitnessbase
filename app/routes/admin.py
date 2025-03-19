from flask import jsonify, request
from sqlalchemy import text
from flask_login import current_user, login_required

@admin.route('/attendance', methods=['GET', 'POST'])
@login_required
@admin_required
def attendance():
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        check_in_time = datetime.now()
        
        # Call the stored procedure to mark attendance
        db.session.execute(text('CALL sp_mark_member_attendance(:member_id, :check_in, :check_out, :staff_id)'),
                         {'member_id': member_id, 
                          'check_in': check_in_time,
                          'check_out': None,
                          'staff_id': current_user.staff_id})
        db.session.commit()
        
        flash('Attendance marked successfully!', 'success')
        return redirect(url_for('admin.attendance'))

    # Get all attendance records
    result = db.session.execute(text('SELECT * FROM fn_get_all_member_attendance()'))
    attendance_records = result.fetchall()

    # Get all members for the dropdown
    members_result = db.session.execute(text('SELECT member_id, full_name FROM gym_members'))
    members = members_result.fetchall()

    return render_template('admin/attendance.html', 
                         attendance_records=attendance_records,
                         members=members)


@admin.route('/sales/add', methods=['POST'])
@login_required
def add_sale():
    try:
        data = request.get_json()
        sale_lines = []
        
        # Convert the sale_details array to sale_line array format
        for item in data['sale_details']:
            if item['item_type'] == 'product':
                sale_lines.append(
                    (
                        'product',
                        item['product_id'],
                        None,
                        item['quantity'],
                        item['unit_price']
                    )::sale_line
                )
            else:
                sale_lines.append(
                    (
                        'item',
                        None,
                        item['item_id'],
                        item['quantity'],
                        item['unit_price']
                    )::sale_line
                )
        
        # Execute the sp_record_sale function
        with db.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT sp_record_sale(
                        p_payment_method := :payment_method,
                        p_received_by_staff_id := :staff_id,
                        p_lines := :sale_lines
                    )
                """),
                {
                    'payment_method': data['payment_method'],
                    'staff_id': current_user.staff_id,
                    'sale_lines': sale_lines
                }
            )
            conn.commit()
            sale_id = result.scalar()
            
            return jsonify({'success': True, 'sale_id': sale_id})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500