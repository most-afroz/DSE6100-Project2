-- Project 2 : Anna Johnson Flooring  (MySQL 8.0+ / MariaDB 10.4+)
-- Run:  mysql -u root -p < db/schema.sql

DROP DATABASE IF EXISTS flooring;
CREATE DATABASE flooring CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flooring;

-- Anna (the contractor) logs in with this table. Only one row is expected.
CREATE TABLE contractor (
    contractor_id   INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE client (
    client_id       INT AUTO_INCREMENT PRIMARY KEY,
    first_name      VARCHAR(50)  NOT NULL,
    last_name       VARCHAR(50)  NOT NULL,
    address         VARCHAR(255) NOT NULL,
    phone           VARCHAR(20)  NOT NULL,
    email           VARCHAR(100) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    card_holder     VARCHAR(100) NOT NULL,
    card_number     CHAR(16)     NOT NULL,
    card_exp_month  TINYINT      NOT NULL,
    card_exp_year   SMALLINT     NOT NULL,
    registered_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_card_digits CHECK (card_number REGEXP '^[0-9]{16}$'),
    CONSTRAINT chk_card_month  CHECK (card_exp_month BETWEEN 1 AND 12),
    CONSTRAINT chk_card_year   CHECK (card_exp_year BETWEEN 2020 AND 2100),
    CONSTRAINT chk_email       CHECK (email LIKE '%_@_%._%')
) ENGINE=InnoDB;

CREATE TABLE product_category (
    category_id     INT AUTO_INCREMENT PRIMARY KEY,
    category_name   VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE product (
    product_id      INT AUTO_INCREMENT PRIMARY KEY,
    category_id     INT          NOT NULL,
    product_name    VARCHAR(100) NOT NULL,
    brand           VARCHAR(100) NOT NULL,
    material_style  VARCHAR(100),
    color           VARCHAR(50),
    unit_price      DECIMAL(10,2) NOT NULL,
    pricing_unit    ENUM('sq_ft','box','piece') NOT NULL DEFAULT 'sq_ft',
    length_in       DECIMAL(6,2),
    width_in        DECIMAL(6,2),
    sqft_per_unit   DECIMAL(8,2),       -- coverage of one box / piece, NULL when priced per sq ft
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (product_name, brand),
    FOREIGN KEY (category_id) REFERENCES product_category(category_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_price    CHECK (unit_price > 0),
    CONSTRAINT chk_dims     CHECK ((length_in IS NULL OR length_in > 0) AND (width_in IS NULL OR width_in > 0)),
    -- a box or piece price is useless without knowing how much floor it covers
    CONSTRAINT chk_coverage CHECK (pricing_unit = 'sq_ft' OR (sqft_per_unit IS NOT NULL AND sqft_per_unit > 0))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- requests
CREATE TABLE flooring_request (
    request_id      INT AUTO_INCREMENT PRIMARY KEY,
    client_id       INT          NOT NULL,
    service_address VARCHAR(255) NOT NULL,
    pref_start_date DATE         NOT NULL,
    pref_end_date   DATE,
    budget          DECIMAL(10,2),
    note            TEXT,
    status          ENUM('pending','quoted','negotiating','accepted','rejected','cancelled')
                    NOT NULL DEFAULT 'pending',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES client(client_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_req_dates  CHECK (pref_end_date IS NULL OR pref_end_date >= pref_start_date),
    CONSTRAINT chk_req_budget CHECK (budget IS NULL OR budget > 0)
) ENGINE=InnoDB;

-- weak entity: a room only exists inside a request
CREATE TABLE request_room (
    room_id          INT AUTO_INCREMENT PRIMARY KEY,
    request_id       INT NOT NULL,
    room_name        VARCHAR(50) NOT NULL,      -- "Kids bedroom", "Upstairs hall" ...
    room_type        ENUM('living room','kitchen','bedroom','bathroom','hallway',
                          'basement','stairs','other') NOT NULL,
    length_ft        DECIMAL(7,2),
    width_ft         DECIMAL(7,2),
    sqft             DECIMAL(9,2) NOT NULL,     -- length*width, or typed in directly
    product_id       INT NOT NULL,              -- desired product
    current_flooring VARCHAR(50),
    removal_required BOOLEAN NOT NULL DEFAULT FALSE,
    install_pattern  ENUM('straight','diagonal','herringbone','chevron','brick','other')
                     NOT NULL DEFAULT 'straight',
    UNIQUE (request_id, room_name),
    FOREIGN KEY (request_id) REFERENCES flooring_request(request_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE RESTRICT,
    CONSTRAINT chk_room_sqft CHECK (sqft > 0),
    CONSTRAINT chk_room_dims CHECK ((length_ft IS NULL AND width_ft IS NULL)
                                 OR (length_ft > 0 AND width_ft > 0))
) ENGINE=InnoDB;

-- photo_no between 1 and 5 plus the UNIQUE pair gives the "max 5 photos" rule in the schema itself
CREATE TABLE request_photo (
    photo_id    INT AUTO_INCREMENT PRIMARY KEY,
    request_id  INT NOT NULL,
    photo_no    TINYINT NOT NULL,
    file_name   VARCHAR(255) NOT NULL,
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (request_id, photo_no),
    FOREIGN KEY (request_id) REFERENCES flooring_request(request_id) ON DELETE CASCADE,
    CONSTRAINT chk_photo_no CHECK (photo_no BETWEEN 1 AND 5)
) ENGINE=InnoDB;

-- total requested area is derived, so I keep it in a view instead of a column that can go stale
CREATE VIEW request_area AS
    SELECT request_id, SUM(sqft) AS total_sqft, COUNT(*) AS room_count
    FROM request_room GROUP BY request_id;

-- ---------------------------------------------------------------- quotes
-- Each new quote is a NEW row with version_no + 1. Old rows are only ever
-- marked 'superseded', their numbers are never changed.
CREATE TABLE quote (
    quote_id        INT AUTO_INCREMENT PRIMARY KEY,
    request_id      INT NOT NULL,
    version_no      INT NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    waste_pct       DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    material_cost   DECIMAL(10,2) NOT NULL,
    labor_cost      DECIMAL(10,2) NOT NULL,
    other_cost      DECIMAL(10,2) NOT NULL DEFAULT 0,   -- can be negative when there is a discount
    total_price     DECIMAL(10,2) NOT NULL,
    proposed_start  DATE NOT NULL,
    proposed_end    DATE,
    note            TEXT,
    status          ENUM('open','superseded','accepted','rejected','cancelled') NOT NULL DEFAULT 'open',
    decided_at      DATETIME,                           -- when client accepted / rejected
    UNIQUE (request_id, version_no),
    FOREIGN KEY (request_id) REFERENCES flooring_request(request_id) ON DELETE RESTRICT,
    CONSTRAINT chk_q_waste CHECK (waste_pct BETWEEN 0 AND 50),
    CONSTRAINT chk_q_money CHECK (material_cost >= 0 AND labor_cost >= 0 AND total_price >= 0),
    CONSTRAINT chk_q_total CHECK (total_price = material_cost + labor_cost + other_cost),
    CONSTRAINT chk_q_dates CHECK (proposed_end IS NULL OR proposed_end >= proposed_start),
    CONSTRAINT chk_q_decided CHECK ((status IN ('accepted','rejected','cancelled')) = (decided_at IS NOT NULL))
) ENGINE=InnoDB;

CREATE TABLE quote_item (
    quote_item_id   INT AUTO_INCREMENT PRIMARY KEY,
    quote_id        INT NOT NULL,
    item_type       ENUM('material','removal','labor','underlayment','trim','stairs',
                         'delivery','other','discount') NOT NULL,
    room_id         INT,           -- set for per-room lines
    product_id      INT,           -- set for material lines
    description     VARCHAR(255) NOT NULL,
    area_sqft       DECIMAL(9,2),  -- room area before waste (material lines)
    quantity        DECIMAL(10,2) NOT NULL DEFAULT 1,
    unit            VARCHAR(20)   NOT NULL DEFAULT 'each',
    unit_price      DECIMAL(10,2) NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (quote_id)   REFERENCES quote(quote_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id)    REFERENCES request_room(room_id) ON DELETE RESTRICT,
    FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE RESTRICT,
    CONSTRAINT chk_qi_material CHECK (item_type <> 'material' OR (product_id IS NOT NULL AND room_id IS NOT NULL)),
    CONSTRAINT chk_qi_sign CHECK ((item_type = 'discount' AND amount <= 0) OR (item_type <> 'discount' AND amount >= 0)),
    CONSTRAINT chk_qi_qty  CHECK (quantity > 0)
) ENGINE=InnoDB;

-- every counterproposal, note, rejection and acceptance is a row here
CREATE TABLE negotiation_message (
    message_id  INT AUTO_INCREMENT PRIMARY KEY,
    request_id  INT NOT NULL,
    quote_id    INT,                        -- the quote being answered, if any
    sender      ENUM('client','contractor') NOT NULL,
    msg_type    ENUM('counter','note','accept','reject','cancel') NOT NULL,
    message     TEXT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES flooring_request(request_id) ON DELETE RESTRICT,
    FOREIGN KEY (quote_id)   REFERENCES quote(quote_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- orders
CREATE TABLE service_order (
    order_id            INT AUTO_INCREMENT PRIMARY KEY,
    quote_id            INT NOT NULL UNIQUE,    -- one accepted quote -> one order
    client_id           INT NOT NULL,
    service_address     VARCHAR(255) NOT NULL,  -- copied so the agreement can't drift
    agreed_price        DECIMAL(10,2) NOT NULL,
    scheduled_start     DATE NOT NULL,
    scheduled_end       DATE,
    status              ENUM('scheduled','in_progress','completed','cancelled') NOT NULL DEFAULT 'scheduled',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actual_install_date DATE,
    completion_date     DATE,
    completion_note     TEXT,
    FOREIGN KEY (quote_id)  REFERENCES quote(quote_id)   ON DELETE RESTRICT,
    FOREIGN KEY (client_id) REFERENCES client(client_id) ON DELETE RESTRICT,
    CONSTRAINT chk_o_price CHECK (agreed_price >= 0),
    CONSTRAINT chk_o_done  CHECK (status <> 'completed' OR completion_date IS NOT NULL),
    CONSTRAINT chk_o_dates CHECK (completion_date IS NULL OR actual_install_date IS NULL
                                  OR completion_date >= actual_install_date)
) ENGINE=InnoDB;

-- one row per room in the order. estimated qty comes from the accepted quote,
-- actual qty is filled when Anna completes the job
CREATE TABLE order_item (
    order_item_id   INT AUTO_INCREMENT PRIMARY KEY,
    order_id        INT NOT NULL,
    room_id         INT NOT NULL,
    product_id      INT NOT NULL,
    installed_sqft  DECIMAL(9,2)  NOT NULL,   -- floor area covered
    est_qty_sqft    DECIMAL(10,2) NOT NULL,   -- area * (1 + waste)
    actual_qty_sqft DECIMAL(10,2),
    unit_price_sqft DECIMAL(10,2) NOT NULL,   -- price per sq ft locked at quote time
    UNIQUE (order_id, room_id),
    FOREIGN KEY (order_id)   REFERENCES service_order(order_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id)    REFERENCES request_room(room_id)   ON DELETE RESTRICT,
    FOREIGN KEY (product_id) REFERENCES product(product_id)     ON DELETE RESTRICT,
    CONSTRAINT chk_oi_qty CHECK (installed_sqft > 0 AND est_qty_sqft > 0
                                 AND (actual_qty_sqft IS NULL OR actual_qty_sqft > 0))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------- bills
-- same versioning idea as quotes: revising a bill inserts version_no + 1
CREATE TABLE bill (
    bill_id     INT AUTO_INCREMENT PRIMARY KEY,
    order_id    INT NOT NULL,
    version_no  INT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount_due  DECIMAL(10,2) NOT NULL,
    note        TEXT,
    status      ENUM('unpaid','disputed','superseded','paid') NOT NULL DEFAULT 'unpaid',
    UNIQUE (order_id, version_no),
    FOREIGN KEY (order_id) REFERENCES service_order(order_id) ON DELETE RESTRICT,
    CONSTRAINT chk_b_amount CHECK (amount_due >= 0),
    CONSTRAINT chk_b_ver    CHECK (version_no >= 1)
) ENGINE=InnoDB;

CREATE TABLE bill_item (
    bill_item_id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id      INT NOT NULL,
    item_type    ENUM('quoted','extra_material','subfloor_repair','extra_labor',
                      'upgrade','discount','credit','other') NOT NULL,
    description  VARCHAR(255) NOT NULL,
    amount       DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (bill_id) REFERENCES bill(bill_id) ON DELETE CASCADE,
    CONSTRAINT chk_bi_sign CHECK ((item_type IN ('discount','credit') AND amount <= 0)
                               OR (item_type NOT IN ('discount','credit') AND amount >= 0))
) ENGINE=InnoDB;

CREATE TABLE bill_message (
    message_id  INT AUTO_INCREMENT PRIMARY KEY,
    bill_id     INT NOT NULL,
    sender      ENUM('client','contractor') NOT NULL,
    msg_type    ENUM('dispute','explanation','revision','note') NOT NULL,
    message     TEXT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bill(bill_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- a bill version is paid in full at most once
CREATE TABLE payment (
    payment_id  INT AUTO_INCREMENT PRIMARY KEY,
    bill_id     INT NOT NULL UNIQUE,
    amount      DECIMAL(10,2) NOT NULL,
    paid_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    card_last4  CHAR(4) NOT NULL,
    FOREIGN KEY (bill_id) REFERENCES bill(bill_id) ON DELETE RESTRICT,
    CONSTRAINT chk_p_amount CHECK (amount >= 0)
) ENGINE=InnoDB;

-- helpful indexes for the dashboard queries
CREATE INDEX idx_req_client   ON flooring_request(client_id);
CREATE INDEX idx_quote_status ON quote(status, decided_at);
CREATE INDEX idx_order_status ON service_order(status);
CREATE INDEX idx_bill_status  ON bill(status, created_at);
