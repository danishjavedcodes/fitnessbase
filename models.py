from sqlalchemy.orm import relationship

class Staff(db.Model):
    __tablename__ = 'staff'
    staff_id = db.Column(db.Integer, primary_key=True)
    # Other columns...

    sales = relationship('Sale', back_populates='received_by', overlaps="received_by,sales_received")

class Sale(db.Model):
    __tablename__ = 'sales'
    sale_id = db.Column(db.Integer, primary_key=True)
    received_by_staff_id = db.Column(db.Integer, db.ForeignKey('staff.staff_id'))
    # Other columns...

    received_by = relationship('Staff', back_populates='sales', overlaps="sales,staff")