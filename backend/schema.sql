CREATE DATABASE IF NOT EXISTS scheduling_manager
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE scheduling_manager;


CREATE TABLE IF NOT EXISTS departments (
    id   INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS teams (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    department_id INT UNSIGNED NOT NULL,
    UNIQUE KEY uq_team_dept_name (department_id, name),
    CONSTRAINT fk_team_dept FOREIGN KEY (department_id)
        REFERENCES departments (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email      VARCHAR(190) NOT NULL UNIQUE,
    name       VARCHAR(120) NOT NULL,
    role       ENUM('user','manager','admin') NOT NULL DEFAULT 'user',
    team_id    INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_team FOREIGN KEY (team_id)
        REFERENCES teams (id) ON DELETE SET NULL,
    INDEX ix_user_team (team_id),
    INDEX ix_user_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS customers (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(160) NOT NULL UNIQUE,
    active     TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INT UNSIGNED NULL,
    CONSTRAINT fk_cust_creator FOREIGN KEY (created_by)
        REFERENCES users (id) ON DELETE SET NULL,
    INDEX ix_customer_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS projects (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(160) NOT NULL UNIQUE,
    active     TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INT UNSIGNED NULL,
    CONSTRAINT fk_proj_creator FOREIGN KEY (created_by)
        REFERENCES users (id) ON DELETE SET NULL,
    INDEX ix_project_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS time_entries (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    entry_date  DATE NOT NULL,
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    entry_type  ENUM('work','customer','standby','break','leave') NOT NULL,
    project_id  INT UNSIGNED NULL,
    customer_id INT UNSIGNED NULL,
    notes       VARCHAR(500) NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_entry_user     FOREIGN KEY (user_id)     REFERENCES users     (id) ON DELETE CASCADE,
    CONSTRAINT fk_entry_project  FOREIGN KEY (project_id)  REFERENCES projects  (id) ON DELETE SET NULL,
    CONSTRAINT fk_entry_customer FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE SET NULL,
    CONSTRAINT ck_entry_times CHECK (end_time > start_time),

    INDEX ix_entry_user_date (user_id, entry_date),
    INDEX ix_entry_date      (entry_date),
    INDEX ix_entry_customer  (customer_id),
    INDEX ix_entry_project   (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS activity_log (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NULL,
    action      VARCHAR(60) NOT NULL,       -- e.g. entry.create, customer.update
    entity_type VARCHAR(40) NULL,
    entity_id   INT UNSIGNED NULL,
    detail      VARCHAR(500) NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE SET NULL,
    INDEX ix_log_created (created_at),
    INDEX ix_log_user    (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
