-- ================================
--  SCHEMA CREATION (Optional)
-- ================================
-- CREATE SCHEMA fitnessbase;
-- SET search_path TO fitnessbase;

-- ==================================
-- 1) Packages
-- ==================================
CREATE TABLE packages (
    package_id         SERIAL PRIMARY KEY,
    package_name       VARCHAR(100) NOT NULL,
    price              NUMERIC(10, 2) NOT NULL,
    duration_in_months INT NOT NULL, 
    trainer_option     VARCHAR(50) NOT NULL 
        CHECK (trainer_option IN ('personal', 'group', 'none')),
    cardio_access      BOOLEAN NOT NULL DEFAULT FALSE,
    sauna_access       SMALLINT NOT NULL DEFAULT 0,
    steam_room_access  SMALLINT NOT NULL DEFAULT 0,
    timings            VARCHAR(50) NOT NULL 
        CHECK (timings IN ('morning', 'evening', 'full day'))
);

-- ==================================
-- 2) Gym Members
-- ==================================
CREATE TABLE gym_members (
    member_id            SERIAL PRIMARY KEY,
    full_name            VARCHAR(100) NOT NULL,
    dob                  DATE NOT NULL,
    phone_number         VARCHAR(15),
    address              TEXT,
    package_id           INT REFERENCES packages(package_id),
    gender               VARCHAR(10) CHECK (gender IN ('male', 'female', 'other')),
    medical_condition    TEXT,
    next_of_kin_name     VARCHAR(100),
    next_of_kin_contact  VARCHAR(15),
    weight               NUMERIC(5, 2),
    height               NUMERIC(5, 2),
    joining_date         DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ==================================
-- 3) Inventory Items
-- ==================================
CREATE TABLE inventory_items (
    item_id             SERIAL PRIMARY KEY,
    item_name           VARCHAR(100) NOT NULL,
    number_of_servings  INT NOT NULL,
    cost_per_serving    NUMERIC(10, 2),
    remaining_servings  INT NOT NULL,
    other_charges       NUMERIC(10, 2),
    date_added          DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ==================================
-- 4) Products
-- ==================================
-- First, drop the dependent tables
DROP TABLE IF EXISTS sale_details CASCADE;
DROP TABLE IF EXISTS product_items CASCADE;
DROP TABLE IF EXISTS products CASCADE;

-- Now recreate the products table with the new structure
CREATE TABLE products (
    product_id   SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    price        NUMERIC(10, 2) NOT NULL,
    description  TEXT
);

-- Recreate the product_items table
CREATE TABLE product_items (
    product_id    INT NOT NULL REFERENCES products(product_id)
        ON DELETE CASCADE,
    item_id       INT NOT NULL REFERENCES inventory_items(item_id)
        ON DELETE CASCADE,
    servings_used INT NOT NULL,
    PRIMARY KEY (product_id, item_id)
);

-- Recreate the sale_details table
CREATE TABLE sale_details (
    sale_detail_id   SERIAL PRIMARY KEY,
    sale_id          INT NOT NULL REFERENCES sales(sale_id)
        ON DELETE CASCADE,
    item_type        VARCHAR(10) NOT NULL 
        CHECK (item_type IN ('product', 'item')),
    product_id       INT REFERENCES products(product_id),
    item_id          INT REFERENCES inventory_items(item_id),
    quantity         INT NOT NULL,
    price            NUMERIC(10, 2) NOT NULL
);

-- Add the constraint after table creation
ALTER TABLE sale_details DROP CONSTRAINT IF EXISTS sale_details_check;

ALTER TABLE sale_details ADD CONSTRAINT sale_details_check
    CHECK (
        (item_type = 'product' AND (product_id IS NOT NULL OR product_id IS NULL) AND item_id IS NULL)
        OR
        (item_type = 'item' AND item_id IS NOT NULL AND product_id IS NULL)
    );
);




-- =========================================
-- PROCEDURE: sp_purchase_package
-- =========================================
-- Usage: 
--   CALL sp_purchase_package(<package_id>, <member_id>, <staff_id_who_receives_payment>);
--
-- This looks up the package's name & duration_in_months from the 'packages' table.
-- Then calculates expiry_date = CURRENT_DATE + (duration_in_months * 1 month).
-- Finally, inserts a record into 'package_sales'.

CREATE OR REPLACE PROCEDURE sp_purchase_package(
    p_package_id   INT,
    p_member_id    INT,
    p_received_by  INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_package_name       packages.package_name%TYPE;
    v_duration_in_months packages.duration_in_months%TYPE;
    v_expiry_date        DATE;
BEGIN
    -- 1) Fetch package details
    SELECT package_name, duration_in_months
      INTO v_package_name, v_duration_in_months
      FROM packages
     WHERE package_id = p_package_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No package found with ID %', p_package_id;
    END IF;
    
    -- 2) Compute expiry date based on package duration
    v_expiry_date := CURRENT_DATE 
                     + (v_duration_in_months * INTERVAL '1 month');
    
    -- 3) Insert new record in package_sales
    INSERT INTO package_sales(
        package_id,
        package_name,
        buying_member_id,
        validity_in_months,
        purchase_date,
        expiry_date,
        received_by
    )
    VALUES (
        p_package_id,
        v_package_name,
        p_member_id,
        v_duration_in_months,
        CURRENT_DATE,
        v_expiry_date,
        p_received_by
    );
END;
$$;

CREATE OR REPLACE FUNCTION fn_get_all_member_details()
RETURNS TABLE(
    member_id INT,
    full_name VARCHAR(100),
    phone_number VARCHAR(15),
    address TEXT,
    gender VARCHAR(10),
    joining_date DATE,
    membership_status VARCHAR(10)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH latest_purchase AS (
        SELECT 
            buying_member_id,
            MAX(expiry_date) AS latest_expiry
        FROM package_sales
        GROUP BY buying_member_id
    )
    SELECT
        m.member_id,
        m.full_name,
        m.phone_number,
        m.address,
        m.gender,
        m.joining_date,
        CASE 
            WHEN lp.buying_member_id IS NULL THEN 'new'::VARCHAR(10)
            WHEN lp.latest_expiry < CURRENT_DATE THEN 'expired'::VARCHAR(10)
            ELSE 'active'::VARCHAR(10)
        END AS membership_status
    FROM gym_members m
    LEFT JOIN latest_purchase lp
           ON m.member_id = lp.buying_member_id
    ORDER BY m.member_id;  -- optional ordering
END;
$$;


CREATE OR REPLACE FUNCTION fn_view_package_sales()
RETURNS TABLE (
    sale_id             INT,
    package_id          INT,
    package_name        VARCHAR(100),
    buyer_member_id     INT,
    buyer_full_name     VARCHAR(100),
    validity_in_months  INT,
    purchase_date       DATE,
    expiry_date         DATE,
    received_by         INT,
    receiver_full_name  VARCHAR(100)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ps.sale_id,
        ps.package_id,
        ps.package_name,
        ps.buying_member_id,
        gm.full_name AS buyer_full_name,
        ps.validity_in_months,
        ps.purchase_date,
        ps.expiry_date,
        ps.received_by,
        st.full_name AS receiver_full_name
    FROM package_sales ps
    JOIN gym_members gm ON ps.buying_member_id = gm.member_id
    LEFT JOIN staff st ON ps.received_by = st.staff_id
    ORDER BY ps.sale_id;
END;
$$;


CREATE OR REPLACE FUNCTION fn_membership_summary_current_month()
RETURNS TABLE (
    total_members bigint,        -- Changed from integer to bigint
    paid_this_month bigint,      -- Changed from integer to bigint
    not_paid_this_month bigint   -- Changed from integer to bigint
) AS $$
BEGIN
    RETURN QUERY
    WITH last_expiry AS (
        SELECT buying_member_id, MAX(expiry_date) AS max_expiry
        FROM package_sales
        GROUP BY buying_member_id
    ),
    mstart AS (
        SELECT date_trunc('month', CURRENT_DATE)::date AS start_of_month
    )
    SELECT
        (SELECT COUNT(*) FROM gym_members)::bigint AS total_members,
        (SELECT COUNT(m.member_id)
         FROM gym_members m
         JOIN last_expiry le ON m.member_id = le.buying_member_id
         CROSS JOIN mstart
         WHERE le.max_expiry >= mstart.start_of_month
        )::bigint AS paid_this_month,
        (
          (SELECT COUNT(*) FROM gym_members)
          -
          (SELECT COUNT(m.member_id)
           FROM gym_members m
           JOIN last_expiry le ON m.member_id = le.buying_member_id
           CROSS JOIN mstart
           WHERE le.max_expiry >= mstart.start_of_month
          )
        )::bigint AS not_paid_this_month;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE PROCEDURE sp_mark_member_attendance(
    p_member_id INT,
    p_check_in_time TIMESTAMP,
    p_check_out_time TIMESTAMP,
    p_marked_by_staff_id INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_existing_attendance_id INT;
BEGIN
    IF p_check_out_time IS NULL THEN
        -- Check for existing active check-in
        SELECT attendance_id INTO v_existing_attendance_id
        FROM member_attendance
        WHERE member_id = p_member_id 
        AND DATE(check_in_time) = DATE(p_check_in_time)
        AND check_out_time IS NULL;
        
        IF FOUND THEN
            RAISE EXCEPTION 'Member already has an active check-in for today';
        END IF;
        
        -- Insert new check-in
        INSERT INTO member_attendance (
            member_id,
            check_in_time,
            marked_by_staff_id
        )
        VALUES (
            p_member_id,
            p_check_in_time,
            p_marked_by_staff_id
        );
    ELSE
        -- Find the active check-in to update
        SELECT attendance_id INTO v_existing_attendance_id
        FROM member_attendance
        WHERE member_id = p_member_id 
        AND DATE(check_in_time) = DATE(p_check_in_time)
        AND check_out_time IS NULL
        ORDER BY check_in_time DESC
        LIMIT 1;
        
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No active check-in found for member % on %', 
                p_member_id, DATE(p_check_in_time);
        END IF;
        
        -- Update with check-out time
        UPDATE member_attendance 
        SET check_out_time = p_check_out_time
        WHERE attendance_id = v_existing_attendance_id;
    END IF;
END;
$$;



CREATE OR REPLACE FUNCTION fn_get_all_member_attendance()
RETURNS TABLE (
    attendance_id INT,
    member_id INT,
    member_name VARCHAR(100),
    check_in_time TIMESTAMP,
    check_out_time TIMESTAMP,
    marked_by_staff_id INT,
    staff_name VARCHAR(100)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ma.attendance_id,
        ma.member_id,
        gm.full_name AS member_name,
        ma.check_in_time,
        ma.check_out_time,
        ma.marked_by_staff_id,
        s.full_name AS staff_name
    FROM member_attendance ma
    JOIN gym_members gm ON ma.member_id = gm.member_id
    LEFT JOIN staff s ON ma.marked_by_staff_id = s.staff_id
    ORDER BY ma.attendance_id;
END;
$$;

CREATE OR REPLACE FUNCTION fn_render_current_items()
RETURNS TABLE (
    item_id INT,
    item_name VARCHAR(100),
    number_of_servings INT,
    cost_per_serving NUMERIC(10, 2),
    remaining_servings INT,
    other_charges NUMERIC(10, 2),
    date_added DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.item_id,
        i.item_name,
        i.number_of_servings,
        i.cost_per_serving,
        i.remaining_servings,
        i.other_charges,
        i.date_added
    FROM inventory_items i
    ORDER BY i.item_id; -- or any other desired sort
END;
$$;


-- Update the render products function to show items
-- Drop the existing function first
DROP FUNCTION IF EXISTS fn_render_current_products();

-- Create the updated function with new return type
CREATE OR REPLACE FUNCTION fn_render_current_products()
RETURNS TABLE (
    product_id INT,
    product_name VARCHAR(100),
    price NUMERIC(10, 2),
    description TEXT,
    items_used JSON
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.product_id,
        p.product_name,
        p.price,
        p.description,
        COALESCE(
            json_agg(
                json_build_object(
                    'item_id', i.item_id,
                    'item_name', i.item_name,
                    'servings_used', pi.servings_used,
                    'remaining_servings', i.remaining_servings,
                    'display_text', i.item_name || ' (' || pi.servings_used || ' servings)'
                ) ORDER BY i.item_name
            ) FILTER (WHERE i.item_id IS NOT NULL),
            '[]'::json
        ) as items_used
    FROM products p
    LEFT JOIN product_items pi ON p.product_id = pi.product_id
    LEFT JOIN inventory_items i ON pi.item_id = i.item_id
    GROUP BY p.product_id, p.product_name, p.price, p.description
    ORDER BY p.product_id;
END;
$$;

-- Add function to check if product can be sold based on inventory
CREATE OR REPLACE FUNCTION fn_check_product_availability(
    p_product_id INT,
    p_quantity INT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_available BOOLEAN := TRUE;
BEGIN
    SELECT BOOL_AND(i.remaining_servings >= (pi.servings_used * p_quantity))
    INTO v_available
    FROM product_items pi
    JOIN inventory_items i ON pi.item_id = i.item_id
    WHERE pi.product_id = p_product_id;
    
    RETURN COALESCE(v_available, FALSE);
END;
$$;

-- Update the existing sp_add_item procedure to handle product relationships
CREATE OR REPLACE PROCEDURE sp_add_item(
    p_item_name VARCHAR(100),
    p_number_of_servings INT,
    p_cost_per_serving NUMERIC(10, 2),
    p_remaining_servings INT,
    p_other_charges NUMERIC(10, 2)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_item_id INT;
BEGIN
    INSERT INTO inventory_items (
        item_name,
        number_of_servings,
        cost_per_serving,
        remaining_servings,
        other_charges,
        date_added
    )
    VALUES (
        p_item_name,
        p_number_of_servings,
        p_cost_per_serving,
        p_remaining_servings,
        p_other_charges,
        CURRENT_DATE
    )
    RETURNING item_id INTO v_item_id;
END;
$$;

-- Add procedure to update item servings
CREATE OR REPLACE PROCEDURE sp_update_item_servings(
    p_item_id INT,
    p_servings_change INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_remaining INT;
BEGIN
    SELECT remaining_servings INTO v_remaining
    FROM inventory_items
    WHERE item_id = p_item_id;
    
    IF v_remaining + p_servings_change < 0 THEN
        RAISE EXCEPTION 'Not enough servings available for item ID %', p_item_id;
    END IF;
    
    UPDATE inventory_items
    SET remaining_servings = remaining_servings + p_servings_change
    WHERE item_id = p_item_id;
END;
$$;

-- Add function to get product inventory status
CREATE OR REPLACE FUNCTION fn_get_product_inventory_status()
RETURNS TABLE (
    product_id INT,
    product_name VARCHAR(100),
    can_be_sold BOOLEAN,
    inventory_status JSON
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.product_id,
        p.product_name,
        fn_check_product_availability(p.product_id, 1) as can_be_sold,
        COALESCE(
            json_agg(
                json_build_object(
                    'item_name', i.item_name,
                    'servings_needed', pi.servings_used,
                    'servings_available', i.remaining_servings,
                    'is_available', i.remaining_servings >= pi.servings_used
                )
            ) FILTER (WHERE i.item_id IS NOT NULL),
            '[]'::json
        ) as inventory_status
    FROM products p
    LEFT JOIN product_items pi ON p.product_id = pi.product_id
    LEFT JOIN inventory_items i ON pi.item_id = i.item_id
    GROUP BY p.product_id, p.product_name
    ORDER BY p.product_id;
END;
$$;


-- Create stored procedure for adding products with items
CREATE OR REPLACE PROCEDURE sp_add_product(
    p_name VARCHAR(100),
    p_price NUMERIC(10, 2),
    p_description TEXT,
    p_items JSON
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_product_id INT;
    v_item JSON;
BEGIN
    -- Insert the product
    INSERT INTO products (product_name, price, description)
    VALUES (p_name, p_price, p_description)
    RETURNING product_id INTO v_product_id;
    
    -- Add items if provided
    IF p_items IS NOT NULL AND json_array_length(p_items) > 0 THEN
        FOR v_item IN SELECT * FROM json_array_elements(p_items)
        LOOP
            INSERT INTO product_items (product_id, item_id, servings_used)
            VALUES (
                v_product_id,
                (v_item->>'item_id')::INT,
                (v_item->>'servings_used')::INT
            );
        END LOOP;
    END IF;
END;
$$;

-- A composite type used as a function parameter/array element.
CREATE TYPE sale_line AS (
    item_type TEXT,          -- 'item' or 'product'
    product_id INT,
    item_id INT,
    quantity INT,
    unit_price NUMERIC(10, 2)
);

CREATE OR REPLACE FUNCTION sp_record_sale(
    p_payment_method TEXT,
    p_received_by_staff_id INT,
    p_lines sale_line[]   -- Array of 'sale_line' composite type
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_sale_id INT;
    v_total_amount NUMERIC(10, 2) := 0;
    v_line sale_line;
    v_item_id INT;
    v_servings_used INT;
    v_items_sold JSONB := '[]'::jsonb;  -- Ensure this is JSONB
BEGIN
    -- 1) Sum the total amount from all line items
    FOREACH v_line IN ARRAY p_lines
    LOOP
        v_total_amount := v_total_amount + (v_line.unit_price * v_line.quantity);
        
        -- Add item details to items_sold JSON
        v_items_sold := jsonb_set(
            v_items_sold,
            '{items}',  -- Correctly specify the path as an array of text
            COALESCE(
                jsonb_agg(
                    jsonb_build_object(
                        'item_type', v_line.item_type,
                        'product_id', v_line.product_id,
                        'item_id', v_line.item_id,
                        'quantity', v_line.quantity,
                        'unit_price', v_line.unit_price
                    )
                ) FILTER (WHERE v_line.item_id IS NOT NULL OR v_line.product_id IS NOT NULL),
                '[]'::jsonb
            ),
            true  -- Ensure create_missing is set to true
        );
    END LOOP;

    -- 2) Insert into 'sales' table (the "header" of the sale)
    INSERT INTO sales (
        sale_timestamp,
        total_amount,
        payment_method,
        received_by_staff_id,
        items_sold
    )
    VALUES (
        NOW(),
        v_total_amount,
        p_payment_method,
        p_received_by_staff_id,
        v_items_sold
    )
    RETURNING sale_id INTO v_sale_id;

    -- 3) For each line item in the array, insert into 'sale_details' and reduce inventory
    FOREACH v_line IN ARRAY p_lines
    LOOP
        -- 3a) Insert the line item into 'sale_details'
        INSERT INTO sale_details (
            sale_id,
            item_type,
            product_id,
            item_id,
            quantity,
            price
        )
        VALUES (
            v_sale_id,
            v_line.item_type,
            v_line.product_id,
            v_line.item_id,
            v_line.quantity,
            v_line.unit_price
        );

        -- 3b) Reduce inventory
        IF v_line.item_type = 'item' THEN
            -- Directly decrement the 'remaining_servings' in 'inventory_items'
            UPDATE inventory_items
               SET remaining_servings = remaining_servings - v_line.quantity
             WHERE item_id = v_line.item_id;

        ELSIF v_line.item_type = 'product' THEN
            -- For each item in 'product_items', reduce inventory by (servings_used * quantity)
            FOR v_item_id, v_servings_used IN
                SELECT item_id, servings_used
                  FROM product_items
                 WHERE product_id = v_line.product_id
            LOOP
                UPDATE inventory_items
                   SET remaining_servings = remaining_servings - (v_servings_used * v_line.quantity)
                 WHERE item_id = v_item_id;
            END LOOP;
        END IF;
    END LOOP;

    -- Return the newly created 'sale_id' in case the application needs it
    RETURN v_sale_id;
END;
$$;

CREATE TABLE staff (
    staff_id               SERIAL PRIMARY KEY,
    full_name              VARCHAR(100) NOT NULL,
    staff_type             VARCHAR(50) 
        CHECK (staff_type IN ('receptionist', 'trainer', 'cleaner', 'manager', 'others')),
    dob                    DATE,
    phone_number           VARCHAR(15),
    address                TEXT,
    gender                 VARCHAR(10) CHECK (gender IN ('male','female','other')),
    next_of_kin_name       VARCHAR(100),
    next_of_kin_phone_number VARCHAR(15),
    salary                 NUMERIC(10,2),
    -- For demonstration, store privileges as an array of text:
    privileges             TEXT[],
    username               VARCHAR(50) UNIQUE NOT NULL,
    password               VARCHAR(255) NOT NULL  -- hashed password, typically
);


-- Staff Attendance Table
CREATE TABLE staff_attendance (
    attendance_id        SERIAL PRIMARY KEY,
    staff_id            INT REFERENCES staff(staff_id),
    check_in_time       TIMESTAMP NOT NULL,
    check_out_time      TIMESTAMP,
    marked_by_staff_id  INT REFERENCES staff(staff_id)
);

-- Function to get all staff attendance
CREATE OR REPLACE FUNCTION fn_get_all_staff_attendance()
RETURNS TABLE (
    staff_attendance_id INT,
    staff_id INT,
    staff_name VARCHAR(100),
    check_in_time TIMESTAMP,
    check_out_time TIMESTAMP,
    marked_by_staff_id INT,
    marked_by_name VARCHAR(100)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        sa.staff_attendance_id,
        sa.staff_id,
        s.full_name AS staff_name,
        sa.check_in_time,
        sa.check_out_time,
        sa.marked_by_staff_id,
        s2.full_name AS marked_by_name
    FROM staff_attendance sa
    JOIN staff s ON sa.staff_id = s.staff_id
    LEFT JOIN staff s2 ON sa.marked_by_staff_id = s2.staff_id
    ORDER BY sa.staff_attendance_id DESC;
END;
$$;

-- Procedure to mark staff attendance
CREATE OR REPLACE PROCEDURE sp_mark_staff_attendance(
    p_staff_id INT,
    p_check_in_time TIMESTAMP,
    p_check_out_time TIMESTAMP,
    p_marked_by_staff_id INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_existing_staff_attendance_id INT;
BEGIN
    IF p_check_out_time IS NULL THEN
        -- Check for existing active check-in
        SELECT staff_attendance_id INTO v_existing_staff_attendance_id
        FROM staff_attendance
        WHERE staff_id = p_staff_id 
        AND DATE(check_in_time) = DATE(p_check_in_time)
        AND check_out_time IS NULL;
        
        IF FOUND THEN
            RAISE EXCEPTION 'Staff member already has an active check-in for today';
        END IF;
        
        -- Insert new check-in
        INSERT INTO staff_attendance (
            staff_id,
            check_in_time,
            marked_by_staff_id
        )
        VALUES (
            p_staff_id,
            p_check_in_time,
            p_marked_by_staff_id
        );
    ELSE
        -- Find the active check-in to update
        SELECT staff_attendance_id INTO v_existing_staff_attendance_id
        FROM staff_attendance
        WHERE staff_id = p_staff_id 
        AND DATE(check_in_time) = DATE(p_check_in_time)
        AND check_out_time IS NULL
        ORDER BY check_in_time DESC
        LIMIT 1;
        
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No active check-in found for staff % on %', 
                p_staff_id, DATE(p_check_in_time);
        END IF;
        
        -- Update with check-out time
        UPDATE staff_attendance 
        SET check_out_time = p_check_out_time
        WHERE staff_attendance_id = v_existing_staff_attendance_id;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION fn_get_all_sales()
RETURNS TABLE (
    sale_id INT,
    sale_date TIMESTAMP,
    items_list TEXT,
    total_amount NUMERIC(10,2),
    payment_method TEXT,
    staff_name VARCHAR(100)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.sale_id,
        s.sale_timestamp,
        string_agg(
            CASE 
                WHEN (item->>'item_type')::TEXT = 'item' THEN 
                    (item->>'name')::TEXT
                ELSE 
                    (item->>'name')::TEXT
            END,
            ', '
        ) as items_list,
        s.total_amount,
        s.payment_method,
        st.full_name as staff_name
    FROM sales s
    CROSS JOIN LATERAL jsonb_array_elements(s.items_sold) as item
    JOIN staff st ON s.received_by_staff_id = st.staff_id
    GROUP BY s.sale_id, s.sale_timestamp, s.total_amount, s.payment_method, st.full_name
    ORDER BY s.sale_timestamp DESC;
END;
$$;
SELECT * FROM fn_get_all_sales();
select * from sales;