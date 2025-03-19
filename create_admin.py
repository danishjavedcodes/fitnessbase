from app import db, create_app
from app.models import Staff
from decimal import Decimal
from datetime import date

def init_admin():
    app = create_app()
    with app.app_context():
        # Check if admin user already exists
        admin = Staff.query.filter_by(username='admin').first()
        if admin is None:
            # Create admin user with full privileges
            admin = Staff(
                full_name='Administrator',
                staff_type='admin',
                dob=date(2000, 1, 1),  # Default date
                phone_number='0000000000',
                address='Admin Office',
                gender='other',
                next_of_kin_name='Emergency Contact',
                next_of_kin_phone_number='0000000000',
                salary=Decimal('0.00'),
                username='admin',
                privileges=['admin', 'dashboard', 'members', 'staff', 'inventory', 'sales', 'reports', 'settings']
            )
            admin.set_password('admin')
            
            db.session.add(admin)
            db.session.commit()
            print('Default admin user created successfully')
        else:
            print('Admin user already exists')

if __name__ == '__main__':
    init_admin()